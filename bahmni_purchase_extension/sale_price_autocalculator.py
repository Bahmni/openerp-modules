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
        if(cost_price_per_unit < 10):
            markup_percentage = 10.0
        elif(cost_price_per_unit < 20):
            markup_percentage = 9.0
        elif(cost_price_per_unit < 30):
            markup_percentage = 7.0
        elif(cost_price_per_unit < 60):
            markup_percentage = 5.0
        elif(cost_price_per_unit < 300):
            markup_percentage = 4.0
        elif(cost_price_per_unit < 400):
            markup_percentage = 3.0
        elif(cost_price_per_unit < 1000):
            markup_percentage = 2.0
        return cost_price + (cost_price * markup_percentage / 100)

    def _calculate_default_sale_price(self, cr, uid, context=None):
        cost_price = self._get_default_cost_price(cr, uid, context=context) or 0.0
        product_uom = self._get_product_uom(cr, uid, context=context)
        return self._calculate_sale_price(cost_price, product_uom)

    _defaults = {
        'sale_price': _calculate_default_sale_price
    }