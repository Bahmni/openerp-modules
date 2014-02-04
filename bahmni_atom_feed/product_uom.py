import logging

from dateutil.relativedelta import relativedelta
from osv import fields, osv
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_uom(osv.osv):

    _name = 'product.uom'
    _inherit = 'product.uom'

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom()

class product_uom_categ(osv.osv):

    _name = 'product.uom.categ'
    _inherit = 'product.uom.categ'

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom_categ()
