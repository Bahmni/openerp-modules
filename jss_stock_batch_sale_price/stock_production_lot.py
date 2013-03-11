from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class jss_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'
    _order = 'life_date'

    def _batch_price(self,cr, uid, ids, context=None):
        for lot in self.browse(cr, uid, ids, context=context):
            if lot.stock_available > 0:
                return lot.sale_price
        return 0

    _columns = {
        'sale_price':fields.float('Sale Price',digits=(4,2)),
        'mrp':fields.float('MRP',digits=(4,2)),
        'cost_price':fields.float('Cost Price',digits=(4,2)),
#        'batch_price': fields.function(_batch_price, string='Batch Price', type='float')

        }

jss_production_lot()
