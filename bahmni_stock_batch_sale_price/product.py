import openerp
from datetime import datetime
import re
from openerp import SUPERUSER_ID
from openerp import pooler, tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging

_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def name_search(self, cr, user, name='', args=None, operator='=ilike', context=None, limit=10):
        if not args:
            args = []
        if name:
            name_starts_with = "%s%%" % name
            ids = list()
            ids.extend(self.search(cr, user, [('default_code','=ilike', name_starts_with)]+ args, order="default_code", limit=limit, context=context))
            if len(ids) < limit:
                args = args + [('id', 'not in', ids)]
                ids.extend(self.search(cr, user, args + [('name', '=ilike', name_starts_with)], order="name", limit=limit, context=context))
            if len(ids) < limit:
                args = args + [('id', 'not in', ids)]
                ids.extend(self.search(cr, user, args + [('default_code', 'ilike', name)], order="default_code", limit=limit, context=context))
            if len(ids) < limit:
                args = args + [('id', 'not in', ids)]
                ids.extend(self.search(cr, user, args + [('name', 'ilike', name)], order="name", limit=limit, context=context))
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cr, user, ids, context=None):

        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        # Extension 
        def _add_category_as_suffix(product, name):
            return name + " (" + product.product_tmpl_id.categ_id.name + ")"

        def _name_get(d, product):
            name = d.get('name','')
            code = d.get('default_code',False)
            if code:
                name = '[%s] %s' % (code,name)
            if d.get('variants'):
                name = name + ' - %s' % (d['variants'],)
            return (d['id'], _add_category_as_suffix(product, name))

        partner_id = context.get('partner_id', False)

        result = []
        for product in self.browse(cr, user, ids, context=context):
            sellers = filter(lambda x: x.name.id == partner_id, product.seller_ids)
            if sellers:
                for s in sellers:
                    mydict = {
                              'id': product.id,
                              'name': s.product_name or product.name,
                              'default_code': s.product_code or product.default_code,
                              'variants': product.variants
                              }
                    result.append(_name_get(mydict, product))
            else:
                mydict = {
                          'id': product.id,
                          'name': product.name,
                          'default_code': product.default_code,
                          'variants': product.variants
                          }
                result.append(_name_get(mydict, product))
        return result

    def get_stock_for_location(self, cr, uid, loc_id, prod_id):
        qty = 0
        cr.execute('''select
                    prodlot_id,
                    qty
                from
                    batch_stock_future_forecast
                where
                    location_id = %s and product_id = %s ''',(loc_id, prod_id,))
        sum_qty = 0.0
        prodlot_qty_map = {}
        for row in cr.dictfetchall():
            if((row['prodlot_id'] != None) ):
                prodlot_qty_map[row['prodlot_id']] = row['qty']
            else :
                sum_qty += row['qty']
        for lot_id, qty in prodlot_qty_map.iteritems():
            prod_lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id)
            if(prod_lot and prod_lot.life_date):
                if(datetime.today() <= datetime.strptime(prod_lot.life_date, DEFAULT_SERVER_DATETIME_FORMAT)):
                    sum_qty += qty

        return sum_qty