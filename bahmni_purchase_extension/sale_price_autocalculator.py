from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class stock_move_split_lines_exist_with_price(osv.osv_memory):
    _name = "stock.move.split.lines"
    _inherit = "stock.move.split.lines"

    def onchange_cost_price(self, cr, uid, ids, cost_price, context=None):
        return {'value': {'sale_price': self._calculate_sale_price(cost_price)}}

    def _calculate_sale_price(self, cost_price):
        cost_price = cost_price or 0.0
        markup_percentage = 1.0
        if(cost_price < 10):
            markup_percentage = 10.0
        elif(cost_price < 20):
            markup_percentage = 9.0
        elif(cost_price < 30):
            markup_percentage = 7.0
        elif(cost_price < 60):
            markup_percentage = 5.0
        elif(cost_price < 300):
            markup_percentage = 4.0
        elif(cost_price < 400):
            markup_percentage = 3.0
        elif(cost_price < 1000):
            markup_percentage = 2.0
        return cost_price + (cost_price * markup_percentage / 100)

    def _calculate_default_sale_price(self, cr, uid, context=None):
        cost_price = self._get_default_cost_price(cr, uid, context=context)
        return self._calculate_sale_price(cost_price)


    _defaults = {
        'sale_price': _calculate_default_sale_price
    }