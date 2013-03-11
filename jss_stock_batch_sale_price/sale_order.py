from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
       # 'batch_price': fields.function(_sale_price, string="Sale Price", type="float"),

    }

sale_order()