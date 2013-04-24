import time
import decimal_precision as dp

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from tools.translate import _
from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare

class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = "stock.picking"

    def onchange_location(self, cr, uid, ids, location_id, location_dest_id, move_lines, context=None):
        for move_line in move_lines:
            move_line[2]['location_id'] = location_id
            move_line[2]['location_dest_id'] = location_dest_id
        return {'value': {'move_lines': move_lines}}