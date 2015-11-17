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
        'group_default_quantity': fields.boolean('Allow to enter default drug Quantity as -1',
            implied_group='bahmni_sale_discount.group_default_quantity'),
        'round_off_by': fields.integer("Round off by"),
    }

    _defaults = {
        'round_off_by': 5,
    }

    def default_get(self, cr, uid, fields, context=None):
        return super(bahmni_sale_configuration, self).default_get(cr, uid, fields, context)

    def set_round_off_by(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, uid, 'sale.config.settings', 'round_off_by', config.round_off_by)
