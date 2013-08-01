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
                expiry_date = datetime.strptime(record.life_date, '%Y-%m-%d')
                expiry = expiry_date.strftime("%b,%Y")
                name = "%s [%s]" % (name,expiry)
            if(context.get('show_future_forcast', False)):
                name =  "%s %s" % (name, record.future_stock_forecast)
            res.append((record.id, name))
        return res

    _columns = {
        'sale_price':fields.float('Sale Price',digits=(4,2)),
        'mrp':fields.float('MRP',digits=(4,2)),
        'cost_price':fields.float('Cost Price',digits=(4,2)),
        'life_date': fields.date('End of Life Date',
            help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.'),
        'use_date': fields.date('Best before Date',
            help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.'),
        'removal_date': fields.date('Removal Date',
            help='This is the date on which the goods with this Serial Number should be removed from the stock.'),
        'alert_date': fields.date('Alert Date',
            help="This is the date on which an alert should be notified about the goods with this Serial Number."),
        'future_stock_forecast': fields.function(_get_future_stock_forecast, type="float", string="Available forecast", select=True,
            help="Future stock forecast quantity of products with this Serial Number available in company warehouses",
            digits_compute=dp.get_precision('Product Unit of Measure')),
    }