from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools
from openerp.tools.sql import drop_view_if_exists

class batch_stock_future_forecast_view(osv.osv):
    _name = "batch.stock.future.forecast"
    _description = "Stock report by batch number considering future availabilty"
    _auto = False
    _columns = {
        'qty': fields.float('Quantity', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True, select=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial Number', readonly=True, select=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'batch_stock_future_forecast')
        cr.execute("""
            create or replace view batch_stock_future_forecast as (
                select max(id) as id,
                    location_id,
                    product_id,
                    prodlot_id,
                    round(sum(qty),6) as qty
                from (
                    select -max(sm.id) as id,
                        sm.location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        -sum(sm.product_qty /uo.factor) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_id)
                    left join product_uom uo
                        on (uo.id=sm.product_uom)
                    where state in ('done', 'confirmed')
                    group by sm.location_id, sm.product_id, sm.product_uom, sm.prodlot_id
                    union all
                    select max(sm.id) as id,
                        sm.location_dest_id as location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        sum(sm.product_qty /uo.factor) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_dest_id)
                    left join product_uom uo
                        on (uo.id=sm.product_uom)
                    where sm.state in ('done', 'confirmed')
                    group by sm.location_dest_id, sm.product_id, sm.product_uom, sm.prodlot_id
                ) as report
                group by location_id, product_id, prodlot_id
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

batch_stock_future_forecast_view()
