import logging
import time
import decimal_precision as dp

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from tools.translate import _
from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import logging
_logger = logging.getLogger(__name__)


class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    def _calculate_balance(self, cr, uid, ids, name, args, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {'prev_amount_outstanding':0.0,'total_outstanding':0.0}
            total_receivable =  self._total_receivable(cr,uid,ids,order,context=context)
            res[order.id]['prev_amount_outstanding'] = total_receivable
            res[order.id]['total_outstanding'] = total_receivable + order.amount_total
        return res

    def _total_receivable(self, cr, uid, ids,order, context=None):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute("""SELECT l.partner_id, a.type, SUM(l.debit-l.credit)
                      FROM account_move_line l
                      LEFT JOIN account_account a ON (l.account_id=a.id)
                      WHERE a.type IN ('receivable','payable')
                      AND l.partner_id = %s
                      AND l.reconcile_id IS NULL
                      GROUP BY l.partner_id, a.type
                      """,(order.partner_id.id,))
        res = {}
        receivable =0.0
        for pid,type,val in cr.fetchall():
            if val is None: val=0
            receivable = (type=='receivable') and val or -val
        return receivable



    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'discount': 0.0,
                'calculated_discount': 0.0,
                }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            total_amount = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']

            if order.chargeable_amount > 0.0:
                res[order.id]['calculated_discount'] = total_amount - order.chargeable_amount;
                self._set_calculated_discount_head(cr, uid, order, res[order.id]['calculated_discount'], context=context)
            elif order.discount_amount == 0.0:
                res[order.id]['calculated_discount'] = total_amount * order.discount_percentage / 100
            else:
                res[order.id]['calculated_discount'] = order.discount_amount
            amount_total_before_round_off = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] - res[order.id]['calculated_discount']
            round_off_amount = self._round_off_amount_for_nearest_five(amount_total_before_round_off)
            res[order.id]['discount'] = res[order.id]['calculated_discount']
            res[order.id]['amount_total'] = amount_total_before_round_off + round_off_amount
            self.write(cr, uid, order.id, {'discount_amount': res[order.id]['calculated_discount'], 'round_off': round_off_amount})
        return res

    def _set_calculated_discount_head(self, cr, uid, order, calculated_discount, context=None):
        calculated_discount_head = self.pool.get('account.account').search(cr, uid, [('name', '=', 'Discount')], context=context)[0]
        calculated_overcharge_head = self.pool.get('account.account').search(cr, uid, [('name', '=', 'Overcharge')], context=context)[0]
        if(not order.discount_acc_id 
            or order.discount_acc_id.id == calculated_discount_head
            or order.discount_acc_id.id == calculated_overcharge_head):

            if(calculated_discount > 0.0):
                self.write(cr, uid, order.id, {'discount_acc_id': calculated_discount_head})
            else:
                self.write(cr, uid, order.id, {'discount_acc_id': calculated_overcharge_head})

    def _round_off_amount_for_nearest_five(self, value):
        remainder = value % 5
        return  -remainder if remainder < 2.5 else 5 - remainder

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        sale_discount = order.discount if order.discount > 0 else order.calculated_discount
        invoice_vals = {
            'name': order.client_order_ref or '',
            'origin': order.name,
            'type': 'out_invoice',
            'reference': order.client_order_ref or order.name,
            'account_id': order.partner_id.property_account_receivable.id,
            'partner_id': order.partner_invoice_id.id,
            'journal_id': journal_ids[0],
            'invoice_line': [(6, 0, lines)],
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': order.payment_term and order.payment_term.id or False,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': order.company_id.id,
            'discount': sale_discount,
            'round_off': order.round_off,
            'discount_acc_id':order.discount_acc_id.id,
            'user_id': order.user_id and order.user_id.id or False,
            'group_id':order.group_id.id,
            'group_description':order.group_description


        }

        # Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
        invoice_vals.update(self._inv_get(cr, uid, order, context=context))
        return invoice_vals

    def _make_invoice(self, cr, uid, order, lines, context=None):
        inv_obj = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        invoiced_sale_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', order.id), ('invoiced', '=', True)], context=context)
        from_line_invoice_ids = []
        for invoiced_sale_line_id in self.pool.get('sale.order.line').browse(cr, uid, invoiced_sale_line_ids, context=context):
            for invoice_line_id in invoiced_sale_line_id.invoice_lines:
                if invoice_line_id.invoice_id.id not in from_line_invoice_ids:
                    from_line_invoice_ids.append(invoice_line_id.invoice_id.id)
        for preinv in order.invoice_ids:
            if preinv.state not in ('cancel',) and preinv.id not in from_line_invoice_ids:
                for preline in preinv.invoice_line:
                    inv_line_id = obj_invoice_line.copy(cr, uid, preline.id, {'invoice_id': False, 'price_unit': -preline.price_unit})
                    lines.append(inv_line_id)
        inv = self._prepare_invoice(cr, uid, order, lines, context=context)
        inv_id = inv_obj.create(cr, uid, inv, context=context)
        DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
        data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv['payment_term'], time.strftime(DEFAULT_SERVER_DATE_FORMAT))
        if data.get('value', False):
            inv_obj.write(cr, uid, [inv_id], data['value'], context=context)
        inv_obj.button_compute(cr, uid, [inv_id])

        return inv_id

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        if states is None:
            states = ['confirmed', 'done', 'exception']
        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_sale_order_line = self.pool.get('sale.order.line')
        partner_currency = {}
        if context is None:
            context = {}
            # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_invoice:
            context['date_invoice'] = date_invoice
        for o in self.browse(cr, uid, ids, context=context):
            currency_id = o.pricelist_id.currency_id.id
            if (o.partner_id.id in partner_currency) and (partner_currency[o.partner_id.id] <> currency_id):
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot group sales having different currencies for the same partner.'))

            partner_currency[o.partner_id.id] = currency_id
            lines = []
            for line in o.order_line:
                if line.invoiced:
                    continue
                elif (line.state in states):
                    lines.append(line.id)
            created_lines = obj_sale_order_line.invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_id.id, []).append((o, created_lines))
        if not invoices:
            for o in self.browse(cr, uid, ids, context=context):
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []), context=context)
                inv_ids = [res]
                invoice_ids.append(res)
                invoice.action_move_create(cr, uid, inv_ids, context)
                invoice.invoice_validate( cr, uid, inv_ids, context)
                invoice_ref = ''
                for o, l in val:
                    invoice_ref += o.name + '|'
                    self.write(cr, uid, [o.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (o.id, res))
                invoice.write(cr, uid, [res], {'origin': invoice_ref, 'name': invoice_ref})
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il, context=context)
                    inv_ids = [res]
                    invoice.action_move_create(cr, uid, inv_ids, context)
                    invoice.invoice_validate(cr, uid, inv_ids, context)
                    invoice_ids.append(res)
                    self.write(cr, uid, [order.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (order.id, res))

            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
            inv = invoice.browse(cr, uid, invoice_ids[0], context=context)

            self.publish_sale_order(cr, uid, ids, context)

            return {
                'name':_("Pay Invoice"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.voucher',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'create':False,
                'edit':False,
                #'url':final_url
                'tag': 'onchange_partner_id',
                'domain': '[]',
                'context': {
                    'default_partner_id': inv.partner_id.id,
                    'default_reference': inv.name,
                    'close_after_process': True,
                    'invoice_type': inv.type,
                    'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                    'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                    'active_ids':'',
                    'active_id':'',
                    'create':False,
                    'edit':False,
                    }
                }

  #  return self.action_view_invoice(cr,uid,ids,context=context)
    def publish_sale_order(self, cr, uid, ids, context=None):
        event_publisher_obj = self.pool.get('event.publisher')
        for order in self.browse(cr, uid, ids, context=context):
            sale_order_items = []
            for line in order.order_line:
                if line.product_id.categ_id.parent_id.name == "Drug" :
                    sale_order_item = {'productUuid': line.product_id.uuid, 'dosage': line.product_dosage, 'numberOfDays': line.product_number_of_days, 'quantity': line.product_uos_qty, 'unit': line.product_uom.name}
                    sale_order_items.append(sale_order_item)
            if sale_order_items :
                data = {'id': order.id, 'saleOrderItems': sale_order_items, 'externalId': order.external_id or None, 'orderDate': order.datetime_order, 'customerId': order.partner_id.ref or None }
                event_publisher_obj.publish_event(cr, uid, 'sale_order', data)

    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in so.invoice_ids]
            #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result


    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
        return super(sale_order, self).create(cr, uid, vals, context=context)

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def _inv_get(self, cr, uid, order, context=None):
        return {}

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def action_wait(self, cr, uid, ids, context=None):
        context = context or {}
        for o in self.browse(cr, uid, ids):
            if not o.order_line:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a sales order which has no line.'))
            noprod = self.test_no_product(cr, uid, o, context)
            if (o.order_policy == 'manual') or noprod:
                self.write(cr, uid, [o.id], {'state': 'manual', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            else:
                self.write(cr, uid, [o.id], {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirmed'})

    def action_button_confirm(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'sale.order', ids[0], 'order_confirm', cr)

        return self.action_invoice_create(cr, uid, ids, False, None,False, context)

    def action_wait(self, cr, uid, ids, context=None):
        context = context or {}
        for o in self.browse(cr, uid, ids):
            if not o.order_line:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a sales order which has no line.'))
            noprod = self.test_no_product(cr, uid, o, context)
            if (o.order_policy == 'manual') or noprod:
                self.write(cr, uid, [o.id], {'state': 'manual', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            else:
                self.write(cr, uid, [o.id], {'state': 'progress', 'date_confirm': fields.date.context_today(self, cr, uid, context=context)})
            self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])
        return True

    def action_quotation_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(context)
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
            }

    def action_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def _get_calculated_discount(self, cr, uid, ids, field_name, field_value, args, context=None):
        return self.write(cr, uid, ids, {'discount_amount': field_value}, context=context)

    def _check_discount_range(self, cr, uid, ids, context=None):
        sale_orders = self.browse(cr, uid, ids, context)
        for sale_order in sale_orders:
            if(sale_order.discount_percentage < 0 or sale_order.discount_percentage > 100):
                return False
        return True

    def _get_partner_village(self, cr, uid, ids, name, args, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            partner_obj = self.pool.get("res.partner")
            partner = partner_obj.browse(cr,uid,order.partner_id.id)
            res[order.id]= partner.village
        return res

    def create(self, cr, uid, vals, context=None):
        if vals.get('datetime_order'):
            date_parsed = datetime.strptime(vals.get('datetime_order'), '%Y-%m-%d %H:%M:%S')
            vals['date_order'] = date_parsed.strftime("%Y-%m-%d")
        return super(sale_order, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid,ids, vals, context=None):
        datetime_val = vals.get('datetime_order')
        if datetime_val:
            date_parsed = datetime.strptime(datetime_val, '%Y-%m-%d %H:%M:%S')
            vals['date_order'] = date_parsed.strftime("%Y-%m-%d")
        return super(sale_order, self).write(cr, uid,ids, vals, context=context)


    _constraints = [
        (_check_discount_range, 'Error!\nDiscount percentage should be between 0-100%.', ['discount_percentage']),
    ]

    _columns = {
    'date_order': fields.date('Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
    'datetime_order': fields.datetime('Date Time', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
    'discount_percentage':fields.float('Discount %',digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly',False)]}),
    'chargeable_amount':fields.float('Final Chargeable Amount',digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly',False)]}),
    'discount_amount':fields.float('Absolute Discount Amount',digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly',False)]}),
    'round_off':fields.float('Amount Round off',digits_compute=dp.get_precision('Account'),readonly=True, states={'draft':[('readonly',False)]}),
    'discount':fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string= 'Discount ',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','discount_percentage', 'chargeable_amount', 'discount', 'calculated_discount'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The calc disc amount."),
    'calculated_discount':fields.function(_amount_all, fnct_inv=_get_calculated_discount, digits_compute=dp.get_precision('Account'), string='Discount Amount', readonly=True, states={'draft':[('readonly',False)]},
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','discount_percentage', 'chargeable_amount','discount', 'calculated_discount'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The calc disc amount."),
    'discount_acc_id': fields.many2one('account.account', 'Discount Account Head', domain=[('parent_id.name', '=', 'Discounts')], readonly=True, states={'draft':[('readonly',False)]}),
    'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='New Charges',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','discount_percentage', 'chargeable_amount','discount', 'calculated_discount'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The amount without tax.", track_visibility='always'),
    'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The tax amount."),
    'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Net Amount',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','discount_percentage', 'chargeable_amount','discount', 'calculated_discount'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The total amount."),
    'prev_amount_outstanding': fields.function(_calculate_balance, digits_compute=dp.get_precision('Account'), string='Previous Balance',
             help="The Previous Outstanding amount.",multi="all"),
    'total_outstanding': fields.function(_calculate_balance, digits_compute=dp.get_precision('Account'), string='Total Outstanding',
             help="The Total Outstanding amount at the time of sale order creation.",multi="all"),
    'partner_village': fields.function(_get_partner_village,type='char',string ='Village',readonly=True),

    }

    _defaults = {
        'datetime_order': lambda self,cr,uid, context=None: str(fields.datetime.context_timestamp(cr, uid, datetime.now().replace(microsecond=0), context=context)),
    }



sale_order()