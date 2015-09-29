from openerp.osv import fields, osv
from openerp.osv.orm import browse_null
from openerp import pooler
import openerp.addons.decimal_precision as dp
import openerp
import logging
import re

_logger = logging.getLogger(__name__)

class product_supplierinfo(osv.osv):
    _name = "product.supplierinfo"
    _inherit = "product.supplierinfo"

    _columns = {
        'manufacturer':fields.char('Manufacturer', size=128, help="Manufacturer of the product supplied."),
    }


class pricelist_partnerinfo(osv.osv):
    _name = "pricelist.partnerinfo"
    _inherit = "pricelist.partnerinfo"

    _columns = {
        'price': fields.float('MRP', digits_compute= dp.get_precision('MRP')),
        'unit_price': fields.float('Unit Price', digits_compute= dp.get_precision('Product Unit Price')),
    }