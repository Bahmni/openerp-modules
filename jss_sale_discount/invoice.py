import time
from lxml import etree
import decimal_precision as dp

import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _

class account_invoice(osv.osv):
    
    _name = "account.invoice"
    _inherit = "account.invoice"
    _description = 'Invoice'

    def _update_discount_head(self, cr, uid, invoice, discount, context=None):
        if context is None:
            context = {}
        #disc_account = self.pool.get('account.account')
        amount_currency = 0.0
        date = time.strftime('%Y-%m-%d')
        l1 = {
                'debit': discount,
                'credit': 0,
                'account_id': invoice.discount_acc_id.id,
                'partner_id': invoice.partner_id.id,
                'ref':invoice.reference,
                'date': date,
				'period_id':invoice.period_id.id,
                #'currency_id':context['currency_id'],
                'amount_currency':amount_currency,
                'company_id': invoice.company_id.id,
                'state': 'valid',
            }

        name = invoice.invoice_line and invoice.invoice_line[0].name or invoice.number
        l1['name'] = name
        lines = [(0, 0, l1)]
		
        acc_journal_id = self.pool.get('account.journal').search(cr, uid,[('name','=','Cash')])[0]
        #acc_journal = self.pool.get('account.journal').browse(cr, uid,acc_journal_id)         
        
        move = {'ref': invoice.reference, 'line_id': lines, 'journal_id': acc_journal_id, 'period_id': invoice.period_id.id, 'date': date}
        move_ids =[]
        move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
        move_ids.append(move_id)
        obj_move_line = self.pool.get('account.move.line')
        line_ids=[]
        for move_new in self.pool.get('account.move').browse(cr,uid,move_ids,context=context):
            for line in move_new.line_id:
                line_ids.append(line.id)
            obj_move_line.write(cr, uid, line_ids,{
                'state': 'valid'
                }, context, check=False)		
        return

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'discount': 0.0,
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['discount']= invoice.discount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed'] - invoice.discount
            #self._update_discount_head(cr,uid, invoice, invoice.discount, context=context)
        return res

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = 0.0
            if invoice.move_id:
                for m in invoice.move_id.line_id:
                    if m.account_id.type in ('receivable','payable'):
                        result[invoice.id] += m.amount_residual_currency
                result[invoice.id] -= invoice.discount
                self._update_discount_head(cr,uid, invoice, invoice.discount, context=context)
        return result

    def _get_invoice_from_line(self, cr, uid, ids, context=None):
        move = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids

    def _get_invoice_from_reconcile(self, cr, uid, ids, context=None):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids, context=context):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids


    _columns={
              
            'discount':fields.float('Discount',digits=(4,2),readonly=True, states={'draft':[('readonly',False)]}),
            'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                    'account.invoice.tax': (_get_invoice_tax, None, 20),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                multi='all'),
            'discount_acc_id': fields.many2one('account.account', 'Discount Account Head', readonly=True, states={'draft': [('readonly', False)]}),
            'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Subtotal', track_visibility='always',
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                    'account.invoice.tax': (_get_invoice_tax, None, 20),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                multi='all'),
            'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax',
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                    'account.invoice.tax': (_get_invoice_tax, None, 20),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                multi='all'),
            'residual': fields.function(_amount_residual, digits_compute=dp.get_precision('Account'), string='Balance',
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line','move_id'], 50),
                    'account.invoice.tax': (_get_invoice_tax, None, 50),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 50),
                    'account.move.line': (_get_invoice_from_line, None, 50),
                    'account.move.reconcile': (_get_invoice_from_reconcile, None, 50),
                    },
                help="Remaining amount due."),

            }
    
    _defaults={
               'discount': 0.0,
               }
    

account_invoice()
