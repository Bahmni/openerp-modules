import time

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from osv import fields, osv
from tools.translate import _
from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare

import itertools
from itertools import izip_longest
import logging
_logger = logging.getLogger(__name__)

def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)

class old_prodlot_move(osv.osv_memory):
    _name = "old.prodlot.move"

    _columns = {
        'location_id': fields.many2one('stock.location', 'Source Location'),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location'),
    }

    def action_move_all_but_latest_batch(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, ['location_id', 'location_dest_id'], context=context)[0]

        location_obj = self.pool.get('stock.location')
        location_id = location_obj.search(cr, uid, [('id', '=', data['location_id'][0])], context=context)[0]
        destination_id = location_obj.search(cr, uid, [('id', '=', data['location_dest_id'][0])], context=context)[0]

        cr.execute('''SELECT prodlots_report.prodlot_id AS prodlot_id,
                             product_template.name AS product_name,
                             prodlots_report.product_id AS product_id,
                             prodlots_report.life_date,
                             prodlots_report.qty AS qty,
                             prodlots_report.unit_id AS unit_id
                      FROM prodlots_report
                      INNER JOIN product_product ON prodlots_report.product_id = product_product.id
                      INNER JOIN product_template ON product_template.id = product_product.product_tmpl_id
                      WHERE prodlots_report.location_id = %s
                            AND prodlots_report.qty > 0
                            AND prodlot_id not in
                            (SELECT distinct prodlot_id FROM stock_move
                             INNER JOIN (SELECT product_id, location_dest_id, max(date) AS date FROM stock_move WHERE prodlot_id IS NOT NULL GROUP BY product_id, location_dest_id) last_moved 
                              ON stock_move.product_id = last_moved.product_id
                                AND stock_move.date = last_moved.date
                                AND stock_move.location_dest_id = last_moved.location_dest_id
                              WHERE stock_move.location_dest_id = %s)
                      ORDER BY prodlots_report.product_id,
                               prodlots_report.life_date;
                    ''', tuple([location_id, location_id]))


        for batch in grouper(cr.dictfetchall(), 100):
            new_stock_picking = {
                'location_id': location_id,
                'location_dest_id': destination_id,
                'move_lines': []
            }
            for row in batch:
                if(row):
                    new_line = {
                        'name': row.get('product_name'),
                        'product_id': row.get('product_id'),
                        'prodlot_id': row.get('prodlot_id'),
                        'product_qty': row.get('qty'),
                        'product_uom': row.get('unit_id'),
                        'location_id': location_id,
                        'location_dest_id': destination_id
                    }
                    new_stock_picking['move_lines'].append((0, 0, new_line))
            _logger.info(new_stock_picking)
            self.pool.get('stock.picking').create(cr, uid, new_stock_picking, context=context)
        return True
