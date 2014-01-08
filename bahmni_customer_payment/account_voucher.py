import time
from lxml import etree

from openerp import netsvc
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import float_compare
import logging
import openerp.exceptions

_logger = logging.getLogger(__name__)


class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = "account.voucher"

    def _calculate_balances(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id] ={'invoice_id':0,
                              'bill_amount':0.0}
            line_ids = sorted(voucher.line_ids, key=lambda v: v.id,reverse=True)
            invoice = None
            for voucher_line in line_ids:
                if(voucher_line.type == 'cr'):
                    inv_no = voucher_line.name
                    inv_ids = self.pool.get("account.invoice").search(cr, uid,[('number','=',inv_no)])
                    if(inv_ids and len(inv_ids) > 0):
                        inv_id = inv_ids[0]
                        invoice = self.pool.get("account.invoice").browse(cr,uid,inv_id,context=context)
                    break
            if(invoice):
                voucher.invoice_id = invoice.id
                res[voucher.id]['bill_amount'] =   invoice.amount_total
                self.write(cr, uid, voucher.id, {'invoice_id': invoice.id})

            if(voucher.state != 'posted'):
                res[voucher.id]['balance_before_pay'] =  self._get_balance_amount(cr,uid,ids,None,None,context)
                res[voucher.id]['balance_amount'] =   self._get_balance_amount(cr,uid,ids,None,None,context) - voucher.amount
                self.write(cr, uid, voucher.id, {'balance_before_pay': res[voucher.id]['balance_before_pay']})
                self.write(cr, uid, voucher.id, {'balance_amount': res[voucher.id]['balance_amount']})

            # if(voucher.state == 'posted'):
            #     #wierd workaround to throw validation error the first time. openerp doesnt support non-blocking messages unless its in on_change
            #     validation_counter()
            #     counter = validation_counter.counter
            #     if(counter%2 !=0):
            #         validation_counter.counter
            #         raise osv.except_osv(_('Warning!'), _('Amount Paid is 0. Do you want to continue?'))

        return res

    def _date_string(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            res[voucher.id]=voucher.date
        return res

    def _get_balance_amount(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        balance = 0.0
        for voucher in self.browse(cr, uid, ids, context=context):
            partner = voucher.partner_id
            balance = partner.credit
        return balance

    def _compute_writeoff_amount(self, cr, uid, line_dr_ids, line_cr_ids, amount, type):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
            debit += l['amount']
        for l in line_cr_ids:
            credit += l['amount']
        return amount - sign * (credit - debit)

    def _convert_to_float(self, amount):
        return amount;

    def _compute_total_balance(self, cr, uid, partner_id,amount):
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr,uid,partner_id)
        return partner.credit - amount

    def _compute_balance_before_pay(self, cr, uid, partner_id,amount):
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr,uid,partner_id)
        return partner.credit - amount

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context=None):
        context = context or {}
        if not line_dr_ids and not line_cr_ids:
            return {'value':{}}
        partner_id = context['partner_id']
        line_osv = self.pool.get("account.voucher.line")
        line_dr_ids = resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount'], context)
        line_cr_ids = resolve_o2m_operations(cr, uid, line_osv, line_cr_ids, ['amount'], context)

        #compute the field is_multi_currency that is used to hide/display options linked to secondary currency on the voucher
        is_multi_currency = False
        if voucher_currency:
            # if the voucher currency is not False, it means it is different than the company currency and we need to display the options
            is_multi_currency = True
        else:
            #loop on the voucher lines to see if one of these has a secondary currency. If yes, we need to define the options
            for voucher_line in line_dr_ids+line_cr_ids:
                company_currency = False
                company_currency = voucher_line.get('move_line_id', False) and self.pool.get('account.move.line').browse(cr, uid, voucher_line.get('move_line_id'), context=context).company_id.currency_id.id
                if voucher_line.get('currency_id', company_currency) != company_currency:
                    is_multi_currency = True
                    break
        balance = self._compute_total_balance(cr, uid, partner_id, amount)
        balance_before_pay = balance + amount
        return {'value': {'writeoff_amount': self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount, type),'balance_amount': balance,'balance_before_pay':balance_before_pay, 'is_multi_currency': is_multi_currency}}

    def _get_writeoff_amount(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        currency_obj = self.pool.get('res.currency')
        res = {}
        debit = credit = 0.0
        for voucher in self.browse(cr, uid, ids, context=context):
            sign = voucher.type == 'payment' and -1 or 1
            for l in voucher.line_dr_ids:
                debit += l.amount
            for l in voucher.line_cr_ids:
                credit += l.amount
            currency = voucher.currency_id or voucher.company_id.currency_id
            res[voucher.id] =  currency_obj.round(cr, uid, currency, voucher.amount - sign * (credit - debit))
        return res


    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        if view_type == 'form':
            if not view_id and context.get('invoice_type'):
                if context.get('invoice_type') in ('out_invoice', 'out_refund'):
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result
            if not view_id and context.get('line_type'):
                if context.get('line_type') == 'customer':
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
                else:
                    result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
                result = result and result[1] or False
                view_id = result

        res = super(account_voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        if context.get('type', 'sale') in ('purchase', 'payment'):
            nodes = doc.xpath("//field[@name='partner_id']")
            for node in nodes:
                node.set('context', "{'search_default_supplier': 1}")
                if context.get('invoice_type','') in ('in_invoice', 'in_refund'):
                    node.set('string', _("Supplier"))
        res['arch'] = etree.tostring(doc)
        return res

    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
            default = super(account_voucher, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date)
            #jss add balance amount
            default['value']['balance_amount'] = self._compute_balance_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
            warning_msg = None
            warning ={}
#            if(price == 0): warning_msg = "Warning!! Amount Paid is 0. Do you want to continue?"
            if(default['value']['balance_amount'] < 0): warning_msg = "Warning!! Amount Paid is more than the Amount Due. Do you want to continue?"
            if(warning_msg):
                warning = {
                    'title': _('Validation Error!'),
                    'message' : warning_msg
                }
                default['warning']= warning
            return default

    def _compute_balance_amount(self, cr, uid, line_dr_ids, line_cr_ids, amount, type):
        amount_unreconciled  = 0.0
        for l in line_dr_ids:
            amount_unreconciled += l['amount_unreconciled']
        for l in line_cr_ids:
            amount_unreconciled += l['amount_unreconciled']
        return amount_unreconciled - amount

    def onchange_amount(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        if context is None:
            context = {}
        res = self.recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        ctx = context.copy()
        ctx.update({'date': date})
        vals = self.onchange_rate(cr, uid, ids, rate, amount, currency_id, payment_rate_currency_id, company_id, context=ctx)
        for key in vals.keys():
            res[key].update(vals[key])
        return res

    def _get_journal(self, cr, uid, context=None):
        if context is None: context = {}
        invoice_pool = self.pool.get('account.invoice')
        journal_pool = self.pool.get('account.journal')
        if context.get('invoice_id', False):
            currency_id = invoice_pool.browse(cr, uid, context['invoice_id'], context=context).currency_id.id
            journal_id = journal_pool.search(cr, uid, [('currency', '=', currency_id)], limit=1)
            return journal_id and journal_id[0] or False
        if context.get('journal_id', False):
            return context.get('journal_id')
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            return context.get('search_default_journal_id')

#        ttype = context.get('type', 'bank')
#        if ttype in ('payment', 'receipt'):
        ttype = 'cash'
        res = self._make_journal_search(cr, uid, ttype, context=context)
        return res and res[0] or False


    _columns={

        'balance_before_pay': fields.float( string='Amount Due',digits=(4,2),readonly=True),
        'balance_amount': fields.float( string='Total Balance',digits=(4,2),readonly=True),
        'create_uid':  fields.many2one('res.users', 'Cashier', readonly=True),
        'invoice_id':fields.many2one('account.invoice', 'Invoice'),
        'bill_amount':fields.function(_calculate_balances, digits_compute=dp.get_precision('Account'), string='Current Bill Amount', multi='all'),
        'date_string':fields.function(_date_string,string='Date',type='char',store=True),

        }
    _defaults = {
        'active': True,
        'journal_id':_get_journal,
        'amount':None,
        'state': 'draft',
        'pay_now': 'pay_now',
        'name': '',
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
        }



def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results

def validation_counter():
    if not hasattr(validation_counter, 'counter'):
        validation_counter.counter = 0  # it doesn't exist yet, so initialize it
    validation_counter.counter += 1

