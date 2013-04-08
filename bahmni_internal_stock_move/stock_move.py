import logging
import openerp
from openerp import SUPERUSER_ID
from openerp import pooler, tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class stock_move(osv.osv):
    _name = "stock.move"
    _inherit = "stock.move"

    def _default_location_destination(self, cr, uid, context=None):
        _logger.debug("********************* in default location ***********************")
        if context is None:
            context = {}
        _logger.debug(context.get('stock_picking_location_dest_id'))
        return context.get('stock_picking_location_dest_id')

    def _default_location_source(self, cr, uid, context=None):
        _logger.debug("********************* in default location ***********************")
        if context is None:
            context = {}
        _logger.debug(context.get('stock_picking_location_id'))
        return context.get('stock_picking_location_id')

    def _default_destination_address(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.partner_id.id

    def _default_move_type(self, cr, uid, context=None):
        """ Gets default type of move
        @return: type
        """
        if context is None:
            context = {}
        picking_type = context.get('picking_type')
        type = 'internal'
        if picking_type == 'in':
            type = 'in'
        elif picking_type == 'out':
            type = 'out'
        return type

    _defaults = {
        'location_id': _default_location_source,
        'location_dest_id': _default_location_destination,
        'partner_id': _default_destination_address,
        'type': _default_move_type,
        'state': 'draft',
        'priority': '1',
        'product_qty': 1.0,
        'scrapped' :  False,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.move', context=c),
        'date_expected': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

stock_move()