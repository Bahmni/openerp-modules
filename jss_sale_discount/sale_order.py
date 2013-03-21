from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_net': 0.0,
                }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']+2
            res[order.id]['amount_net'] = res[order.id]['amount_total'] - res[order.id]['discount']
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
    'discount':fields.float('Discount',digits=(4,2),readonly=True, states={'draft':[('readonly',False)]}),
    'discount_head': fields.selection((('M','Malaria'), ('TB','TB')),'Discount Head' ),
    'amount_net': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Net Amount',
        store = True,multi='sums', help="The amount after additional discount."),
    'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The amount without tax.", track_visibility='always'),
    'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The tax amount."),
    'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
        store={
            'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
            'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
        multi='sums', help="The total amount."),

    }

sale_order()