from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class jss_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'
    _order = 'life_date'


    _columns = {
        'sale_price':fields.float('Sale Price',digits=(4,2)),
        'mrp':fields.float('MRP',digits=(4,2)),
        'cost_price':fields.float('Cost Price',digits=(4,2)),
        'life_date': fields.date('End of Life Date',
            help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.'),
        'use_date': fields.date('Best before Date',
            help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.'),
        'removal_date': fields.date('Removal Date',
            help='This is the date on which the goods with this Serial Number should be removed from the stock.'),
        'alert_date': fields.date('Alert Date',
            help="This is the date on which an alert should be notified about the goods with this Serial Number."),

        }

jss_production_lot()
