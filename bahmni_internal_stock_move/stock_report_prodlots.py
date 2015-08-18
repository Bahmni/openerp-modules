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
from openerp import tools
from openerp.tools.sql import drop_view_if_exists

class prodlots_report(osv.osv):
    _name = "prodlots.report"
    _description = "Stock report by serial number"
    _auto = False
    _columns = {
        'qty': fields.float('Quantity', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True, select=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial Number', readonly=True, select=True),
        'life_date': fields.date('Expiry Date', readonly=True),
        'unit_id': fields.many2one('product.uom', 'Units', readonly=True, select=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'prodlots_report')
        cr.execute("""
            create or replace view prodlots_report as (
            select 
              batch_stock_future_forecast.id,
              location_id, 
              prodlot_id, 
              (qty * product_uom.factor) as qty,
              batch_stock_future_forecast.product_id, 
              life_date, 
              product_uom.id as unit_id
            from
              batch_stock_future_forecast
            left join product_product on (product_product.id=batch_stock_future_forecast.product_id)
            left join product_template on (product_template.id=product_product.product_tmpl_id)
            left join product_uom on (product_uom.id=product_template.uom_id)
            left join stock_production_lot spl on spl.id = batch_stock_future_forecast.prodlot_id
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

prodlots_report()
