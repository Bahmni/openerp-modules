from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
        'external_id'   : fields.char('external_id', size=64),
        'group_id'      : fields.many2one('visit', 'Group Reference', required=False, select=True, readonly=True),
        'group_description':fields.char('Visit', 15),
    }

class sale_order_group(osv.osv):
    _name = "visit"
    _table = "sale_order_group"

    def __str__(self):
        return "Visit"

    _columns = {
        'group_id'      : fields.char('group_id', 38),
        'description'   : fields.char('visit', 40),
        'type'          : fields.char('type', 15)
    }


class sale_order_line(osv.osv):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    _columns = {
        'external_id': fields.char('external_id', size=64),
    }
