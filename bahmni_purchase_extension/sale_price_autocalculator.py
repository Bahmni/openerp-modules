from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class stock_move_split_lines_exist_with_price(osv.osv_memory):
    _name = "stock.move.split.lines"
    _inherit = "stock.move.split.lines"

    def onchange_cost_price(self, cr, uid, ids, cost_price, context=None):
        cost_price = cost_price or 0.0
        product_uom = self._get_product_uom(cr, uid, context=context)
        return {'value': {'sale_price': self._calculate_sale_price(cost_price, product_uom)}}

    def _calculate_sale_price(self, cost_price, product_uom):
        cost_price = cost_price or 0.0
        product_uom_factor = product_uom.factor if(product_uom is not None) else 1.0
        cost_price_per_unit = cost_price * product_uom_factor
        markup_percentage = 1.0
        price_markup_table = [
            [0.0,   1.0,    10.0],
            [1.0,   3.0,    9.0],
            [3.0,   6.0,    8.0],
            [6.0,   15.0,   7.0],
            [15.0,  35.0,   6.0],
            [35.0,  100.0,  5.0],
            [100.0, 250.0,  4.0],
            [250.0, 600.0,  3.0],
            [600.0, 1000.0, 2.0],
            [1000.0,None,   1.0],
        ]
        for (lower, higher, markup_per) in price_markup_table:
            if ((cost_price_per_unit > lower and cost_price_per_unit <= higher) or
                (cost_price_per_unit > lower and higher is None)):
                markup_percentage = markup_per
        return cost_price + (cost_price * markup_percentage / 100)

    def _calculate_default_sale_price(self, cr, uid, context=None):
        cost_price = self._get_default_cost_price(cr, uid, context=context) or 0.0
        product_uom = self._get_product_uom(cr, uid, context=context)
        return self._calculate_sale_price(cost_price, product_uom)

    _defaults = {
        'sale_price': _calculate_default_sale_price
    }