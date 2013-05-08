
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc
import logging

_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    
    _name = 'product.product'
    _inherit = 'product.product'

    # extending this method from stock.product to list only unexpired products
    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        shop_obj = self.pool.get('sale.shop')
        
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res

        if context.get('shop', False):
            warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id

        if context.get('warehouse', False):
            lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search(cr, uid, [], context=context)
            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids

        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        uom_ids = []
        for product in self.read(cr, uid, ids, ['uom_id'], context=context):
            product2uom[product['id']] = product['uom_id'][0]
            uom_ids.append(product['uom_id'][0])
        # this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
        uoms_o = {}
        for uom in self.pool.get('product.uom').browse(cr, uid, uom_ids, context=context):
            uoms_o[uom.id] = uom

        results = []
        results2 = []

        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "sm.date>=%s and sm.date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "sm.date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "sm.date<=%s"
            date_values = [to_date]
        if date_values:
            where.append(tuple(date_values))

        prodlot_id = context.get('prodlot_id', False)
        prodlot_clause = ' and (spl.life_date is null or spl.life_date > now()) '
        if prodlot_id:
            prodlot_clause = ' and prodlot_id = %s '
            where += [prodlot_id]

        # TODO: perhaps merge in one query.
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            cr.execute(
                'select sum(sm.product_qty), sm.product_id, sm.product_uom '\
                'from stock_move sm '\
                'left outer join stock_production_lot spl on sm.prodlot_id = spl.id '\
                'where '\
                'sm.location_id NOT IN %s '\
                'and sm.location_dest_id IN %s '\
                'and sm.product_id IN %s '\
                'and sm.state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
                + prodlot_clause +
                'group by sm.product_id,sm.product_uom',tuple(where))
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute(
                'select sum(sm.product_qty), sm.product_id, sm.product_uom '\
                'from stock_move sm '\
                'left outer join stock_production_lot spl on sm.prodlot_id = spl.id '\
                'where '\
                'sm.location_id IN %s '\
                'and sm.location_dest_id NOT IN %s '\
                'and sm.product_id  IN %s '\
                'and sm.state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                + prodlot_clause +
                'group by sm.product_id,sm.product_uom',tuple(where))
            results2 = cr.fetchall()

        # Get the missing UoM resources
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
            for o in uoms:
                uoms_o[o.id] = o

        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] -= amount
        return res

    def _check_low_stock(self, cr, uid, ids, field_name, arg, context=None):
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        for product in self.browse(cr, uid, ids, context=context):
            orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
            if (len(orderpoints) > 0 and product.virtual_available < orderpoints[0].product_min_qty):
                return True
            else:
                return False
        return False

    def _search_low_stock(self, cr, uid, obj, name, args, context=None):
        ids = set()
        context = context or {}
        location = context.get('location', False)
        location_condition = ""
        if(location):
            location_condition = "where location_id=" + str(location)
        for cond in args:
            cr.execute("select product_id from stock_warehouse_orderpoint " + location_condition)
            product_ids = set(id[0] for id in cr.fetchall())
            for product in self.browse(cr, uid, list(product_ids), context=context):
                orderpoints = sorted(product.orderpoint_ids, key=lambda orderpoint: orderpoint.product_min_qty, reverse=True)
                if (len(orderpoints) > 0 and product.virtual_available < orderpoints[0].product_min_qty):
                    ids.add(product.id)
        if ids:
            return [('id', 'in', tuple(ids))]
        return [('id', '=', '0')]

    _columns = {
        'drug':fields.char('Drug Name', size=64),
        'manufacturer':fields.char('Manufacturer', size=64),
        'low_stock': fields.function(_check_low_stock, type="boolean", string="Low Stock", fnct_search=_search_low_stock)
    }