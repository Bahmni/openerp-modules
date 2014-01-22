from osv import fields, osv
from tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    
    _name = 'product.product'
    _inherit = 'product.product'

    _columns = {
        'dhis2_code': fields.char('DHIS2 Code'),
    }

class res_company(osv.osv):
    
    _name = 'res.company'
    _inherit = 'res.company'

    _columns = {
        'dhis2_code': fields.char('DHIS2 Code'),
    }
