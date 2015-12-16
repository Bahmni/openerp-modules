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
            balance = partner.credit or partner.debit
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

    def _compute_total_balance(self, cr, uid, partner_id, amount, context=None):
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr,uid,partner_id)
        balance = partner.credit or partner.debit
        return balance - amount

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
        balance = self._compute_total_balance(cr, uid, partner_id, amount, context=context)
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
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if context is None:
            context = {}
        context_multi_currency = context.copy()
        if date:
            context_multi_currency.update({'date': date})

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')

        #set default values
        default = {
            'value': {'line_dr_ids': [] ,'line_cr_ids': [] ,'pre_line': False,},
        }

        #drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        if line_ids:
            line_pool.unlink(cr, uid, line_ids)

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        currency_id = currency_id or journal.company_id.currency_id.id
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id

        if journal.type not in ('cash', 'bank'):
            return default

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'

        #JSS Change START - if price is negative, add to total debit/credit
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = price if price >=0.0 else 0.0
            total_credit = -price if price <0.0 else 0.0
        else:
            total_debit = -price if price <0.0 else 0.0
            total_credit = price if price >= 0.0 else 0.0
            account_type = 'receivable'
        #JSS Change END - if price is negative, add to total debit/credit

        if not context.get('move_line_ids', False):
            ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
        else:
            ids = context['move_line_ids']
        invoice_id = context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id.id
        move_line_found = False

        #order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        #compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue
            if invoice_id:
                if line.invoice.id == invoice_id:
                    #if the invoice linked to the voucher line is equal to the invoice_id in context
                    #then we assign the amount on that line, whatever the other voucher lines
                    move_line_found = line.id
                    break
            elif currency_id == company_currency:
                #otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    #if the amount residual is equal the amount voucher, we assign it to that voucher
                    #line, whatever the other voucher lines
                    move_line_found = line.id
                    break
                #otherwise we will split the voucher amount on each line (by most old first)

                #JSS Change START (adding residual amount to total_credit/debit)
                total_credit += line.credit and line.amount_residual or 0.0
                total_debit += line.debit and line.amount_residual_currency or 0.0
                #JSS Change END

            elif currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_line_found = line.id
                    break
                total_credit += line.credit and line.amount_currency or 0.0
                total_debit += line.debit and line.amount_currency or 0.0
        #voucher line creation
        for line in account_move_lines:

            if _remove_noise_in_o2m():
                continue

            if line.currency_id and currency_id==line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0)
                amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual))
            line_currency_id = line.currency_id and line.currency_id.id or company_currency
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (move_line_found == line.id) and min(abs(price), amount_unreconciled) or 0.0,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }

            #in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            #on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_line_found:
                if currency_id == line_currency_id:
                    _logger.info("reduce amount")
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount

            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)

        #jss add balance amount
        default['value']['balance_amount'] = self._compute_balance_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        if(default['value']['balance_amount'] < 0):
            default['warning'] = {
                'title': _('Validation Error!'),
                'message' : "Warning!! Amount Paid is more than the Amount Due. Do you want to continue?"
            }
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

