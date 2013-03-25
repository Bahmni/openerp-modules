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
    
    def _amount_net(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_total': 0.0,
                'amount_net': 0.0,
                'discount': 0.0,
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_total'] += line.price_subtotal
            res[invoice.id]['discount']= invoice.discount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_total'] - invoice.discount
            res[invoice.id]['amount_net'] = res[invoice.id]['amount_total']
        return res

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_net': 0.0,
                'discount': 0.0,
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['discount']= invoice.discount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed'] - invoice.discount
            res[invoice.id]['amount_net'] = res[invoice.id]['amount_total']
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
            'amount_net': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), string='Net',
                                            store=True,multi='all'),
            'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                store={
                    'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                    'account.invoice.tax': (_get_invoice_tax, None, 20),
                    'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
                    },
                multi='all'),
			'discount_head': fields.char('Discount Head' ),
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
