import time

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from tools.translate import _
from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, \
    float_compare

import itertools
from itertools import izip_longest
import logging

_logger = logging.getLogger(__name__)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)


class fix_forcasted_quantity(osv.osv_memory):
    _name = "fix.forcasted.quantity"

    _columns = {
        'location_id': fields.many2one('stock.location', 'Source Location'),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location'),
        'product_id': fields.many2one('product.product', 'Product Id'),
    }

    def action_fix(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, ['location_id', 'location_dest_id', 'product_id'], context=context)[0]

        location_obj = self.pool.get('stock.location')
        destination_id = location_obj.search(cr, uid, [('id', '=', data['location_dest_id'][0])], context=context)[0]
        source_id = location_obj.search(cr, uid, [('id', '=', data['location_id'][0])], context=context)[0]
        product_obj = self.pool.get('product.product')
        product_id = product_obj.search(cr, uid, [('id', '=', data['product_id'][0])], context=context)[0]

        cr.execute('''SELECT
            pp.name_template as product_name,
            coalesce(incoming_qty.prodlot_id, outgoing_qty.prodlot_id)    AS prodlot_id,
            coalesce(incoming_qty.product_id, outgoing_qty.product_id)    AS product_id,
            coalesce(outgoing_qty.sum, 0) - coalesce(incoming_qty.sum, 0) AS qty,
            coalesce(outgoing_qty.unit_id, incoming_qty.unit_id) as unit_id
            FROM (SELECT
                    sum(sm.product_qty),
                    sm.product_id,
                    sm.prodlot_id,
                    sm.product_uom as unit_id
                    FROM stock_move sm
                    LEFT OUTER JOIN stock_production_lot spl ON sm.prodlot_id = spl.id
                    WHERE sm.product_id = %s AND sm.state IN ('done', 'assigned', 'waiting', 'confirmed')
                    AND sm.location_id = %s
                    AND (spl.life_date IS NULL OR spl.life_date > now())
                    GROUP BY sm.prodlot_id, sm.product_id, sm.product_uom) AS outgoing_qty
            FULL OUTER JOIN (SELECT
                    sum(sm.product_qty),
                    sm.product_id,
                    sm.prodlot_id,
                    sm.product_uom as unit_id
                    FROM stock_move sm
                    LEFT OUTER JOIN stock_production_lot spl ON sm.prodlot_id = spl.id
                    WHERE sm.product_id = %s AND sm.state IN ('done', 'assigned', 'waiting', 'confirmed')
                         AND sm.location_dest_id = %s
                         AND (spl.life_date IS NULL OR spl.life_date > now())
                    GROUP BY sm.prodlot_id, sm.product_id, sm.product_uom) AS incoming_qty
            ON (incoming_qty.product_id = outgoing_qty.product_id AND
                (incoming_qty.prodlot_id = outgoing_qty.prodlot_id))
            JOIN product_product pp ON pp.id = coalesce(incoming_qty.product_id, outgoing_qty.product_id)
            WHERE coalesce(incoming_qty.sum, 0) < coalesce(outgoing_qty.sum, 0);''', tuple([product_id, destination_id, product_id, destination_id]))

        for batch in grouper(cr.dictfetchall(), 100):
            new_stock_picking = {
                'location_id': source_id,
                'location_dest_id': destination_id,
                'move_lines': []
            }
            for row in batch:
                if (row):
                    new_line = {
                        'name': row.get('product_name'),
                        'product_id': row.get('product_id'),
                        'prodlot_id': row.get('prodlot_id'),
                        'product_qty': row.get('qty'),
                        'product_uom': row.get('unit_id'),
                        'location_id': source_id,
                        'location_dest_id': destination_id
                    }
                    new_stock_picking['move_lines'].append((0, 0, new_line))
            _logger.info(new_stock_picking)
            self.pool.get('stock.picking').create(cr, uid, new_stock_picking, context=context)
        return True
