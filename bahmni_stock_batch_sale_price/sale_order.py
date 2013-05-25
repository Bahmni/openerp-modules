import decimal_precision as dp
from datetime import datetime
from osv import fields, osv
from tools.translate import _
from openerp import tools, SUPERUSER_ID

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
        'date_order': fields.datetime('Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
    }

    _defaults = {
        'date_order': lambda self,cr,uid, context=None: str(fields.datetime.context_timestamp(cr, uid, datetime.now().replace(microsecond=0), context=context)),
    }

sale_order()