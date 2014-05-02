import logging

from openerp.osv import fields, osv
from openerp import pooler
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class bahmni_sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'group_final_so_charge': fields.boolean('Allow to enter final Sale Order Charge',
            implied_group='bahmni_sale_discount.group_final_so_charge'),
    }

    def default_get(self, cr, uid, fields, context=None):
        return super(bahmni_sale_configuration, self).default_get(cr, uid, fields, context)
