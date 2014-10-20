from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)



class processed_drug_order(osv.osv):
    _name = "processed.drug.order"

    _columns = {
        'order_uuid'      : fields.char('Order UUID', size=38, required=True)
    }
