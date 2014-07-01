from osv import fields, osv
from datetime import datetime
from tools.translate import _
import decimal_precision as dp
import netsvc
import logging
_logger = logging.getLogger(__name__)


class stock_production_lot(osv.osv):

    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'
    _order = 'life_date'

    def _get_future_stock_forecast(self, cr, uid, ids, field_name, arg, context=None):
        """ Gets stock of products for locations
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        if 'location_id' not in context:
            locations = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'internal')], context=context)
        else:
            locations = context['location_id'] and [context['location_id']] or []

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}.fromkeys(ids, 0.0)
        if locations:
            cr.execute('''select
                    prodlot_id,
                    sum(qty)
                from
                    batch_stock_future_forecast
                where
                    location_id IN %s and prodlot_id IN %s group by prodlot_id''',(tuple(locations),tuple(ids),))
            res.update(dict(cr.fetchall()))

        product_uom_id = context.get('product_uom', None)
        if(product_uom_id):
            product_uom = self.pool.get('product.uom').browse(cr, uid, product_uom_id, context)
            for key in res:
                res[key] = res[key] * product_uom.factor

        return res

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if(record.life_date):
                expiry_date = datetime.strptime(record.life_date, '%Y-%m-%d %H:%M:%S')
                expiry = expiry_date.strftime("%b,%Y")
                name = "%s [%s]" % (name,expiry)
            if(context.get('show_future_forcast', False)):
                name =  "%s %s" % (name, record.future_stock_forecast)
            res.append((record.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        ids = []
        if(context.get('only_available_batch', False)):
            batch_stock_query = 'select prodlot_id from batch_stock_future_forecast where qty > 0'
            for column,operator,value in args:
                if(column == "product_id"):
                    batch_stock_query += " and product_id = %s" % value
            if context.get('location_id', False):
                batch_stock_query += " and location_id = %s" % context['location_id']
            cr.execute(batch_stock_query)
            args += [('id', 'in', [row[0] for row in cr.fetchall()])]

        if name:
            ids = self.search(cr, uid, [('prefix', '=', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, uid, [('name', 'ilike', name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)

    _columns = {
        'sale_price':fields.float('Sale Price',digits=(4,2)),
        'mrp':fields.float('MRP',digits=(4,2)),
        'cost_price':fields.float('Cost Price',digits=(4,2)),
        'future_stock_forecast': fields.function(_get_future_stock_forecast, type="float", string="Available forecast", select=True,
            help="Future stock forecast quantity of products with this Serial Number available in company warehouses",
            digits_compute=dp.get_precision('Product Unit of Measure')),
    }

stock_production_lot()