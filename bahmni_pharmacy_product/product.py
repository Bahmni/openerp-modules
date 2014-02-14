
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import uuid

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
            warehouse_ids = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id']
            warehouse_id = None;
            if(warehouse_ids and len(warehouse_ids) > 0):
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

    def _get_actual_stock(self, cr, uid, ids, field_name, arg, context=None):
        context = context or {}
        ctx = context.copy()
        ctx.update({ 'states': ('done',), 'what': ('in', 'out')})
        if(ctx.get('location', False)):
            ctx.update({'compute_child': False})
        return self.get_product_available(cr, uid, ids, context=ctx)


    def unlink(self, cr, uid, ids, context=None):
        for id in ids:
            self.raise_event(cr, uid,{'isDeleted' : True}, id)
        res = super(product_product, self).unlink(cr,uid,ids,context)
        return res

    def create(self, cr, uid, data, context=None):
        if data.get("uuid") is None:
            data['uuid'] = str(uuid.uuid4())

        prod_id = super(product_product, self).create(cr, uid, data, context)

        data_to_be_published = {
            'uuid':data.get('uuid',''),
            'name':data.get('name',''),
            'list_price':data.get('list_price' ,0.0),
            'standard_price':data.get('standard_price',0.0) ,
            'life_time':data.get('life_time',None),
            'drug':data.get('drug',''),
            'default_code':data.get('default_code',''),
            'manufacturer':data.get('manufacturer',''),
            'description':data.get('description',False),
            'category':data.get('category',''),
            'categ_id':data.get('categ_id',''),
            }
        self.raise_event(cr, uid,data_to_be_published, prod_id)
        return prod_id

    def write(self, cr, uid, ids, vals, context=None):
        status = super(product_product, self).write(cr, uid, ids, vals, context=context)
        if (len(vals)==1) and (("message_follower_ids" in vals) or "image" in vals) :
            return status
        self.raise_event(cr, uid,vals, ids[0])
        return status

    def raise_event(self, cr,uid, data, prod_id):
        data['id'] = prod_id
        prod_obj = self.pool.get('product.product')
        prod = prod_obj.browse(cr,uid,prod_id)

#        if((data.get('uuid',None) == None) or (data.get('uuid',None) == False)):
        data.pop('uuid',None)
        if(prod.uuid == False or prod.uuid == None):
            return
        data['uuid'] = prod.uuid

        description = data.get('description',False)
        data.pop('description',None) if(description == False) else None

        data.pop('categ_id',None)
        data['category'] = prod.categ_id.name

        data.pop('active', None)
        data['status'] = 'active' if(prod.active) else 'inactive'

        if(data.get('isDeleted',False)):
            data.pop('isDeleted', None)
            data['status'] = 'deleted'

        event_publisher_obj = self.pool.get('event.publisher')
        event_publisher_obj.publish_event(cr, uid, 'product', data)

    _columns = {
        'uuid': fields.char('UUID', size=64),
        'drug':fields.char('Drug Name', size=64),
        'manufacturer':fields.char('Manufacturer', size=64),
        'low_stock': fields.function(_check_low_stock, type="boolean", string="Low Stock", fnct_search=_search_low_stock),
        'actual_stock': fields.function(_get_actual_stock, type="float", string="Actual Stock"),
    }
