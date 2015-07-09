# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists

class prod_last_moved_report(osv.osv):
    _name = "prod_last_moved.report"
    _description = "Products report by last moved"
    _auto = False
    _order = 'last_moved_date desc'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
        'origin': fields.text('Source', readonly=True),
        'location_id': fields.many2one('stock.location', 'Source Location', readonly=True, select=True),
        'last_moved_date': fields.date('Last Moved Date', readonly=True)
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'prod_last_moved_report')
        cr.execute("""
            create or replace view prod_last_moved_report as (
                SELECT
                  sm.id,
                  sm.name            AS desc,
                  sm.origin,
                  sm.location_id,
                  sm.product_id,
                  stock_picking_time AS last_moved_date
                FROM stock_move sm
                    JOIN (
                           SELECT
                             max(id) AS id
                           FROM stock_move osm
                           WHERE (product_id, stock_picking_time) IN
                                 (SELECT
                                    sm.product_id,
                                    max(sm.stock_picking_time)
                                  FROM stock_move sm
                                    JOIN stock_location sl ON sm.location_dest_id = sl.id AND sl.name = 'Customers'
                                  GROUP BY product_id)
                           GROUP BY product_id) AS csm
                      ON sm.id = csm.id
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

prod_last_moved_report()
