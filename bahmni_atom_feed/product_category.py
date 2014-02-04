import logging

from dateutil.relativedelta import relativedelta
from osv import fields, osv
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_category(osv.osv):

    _name = 'product.category'
    _inherit = 'product.category'

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }

product_category()
