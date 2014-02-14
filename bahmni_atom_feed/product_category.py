import logging

from dateutil.relativedelta import relativedelta
import uuid
from osv import fields, osv
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_category(osv.osv):

    _name = 'product.category'
    _inherit = 'product.category'

    def create(self, cr, uid, data, context=None):
        if data.get("uuid") is None:
            data['uuid'] = str(uuid.uuid4())

        prod_id = super(product_category, self).create(cr, uid, data, context)
        return prod_id

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }

product_category()
