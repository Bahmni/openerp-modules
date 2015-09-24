import json
import logging

from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp import tools
from openerp.osv import fields, osv
from itertools import groupby
from datetime import date, datetime


_logger = logging.getLogger(__name__)


class order_save_service(osv.osv):
    _name = 'order.save.service'
    _auto = False

    def _create_sale_order_line(self, cr, uid, name, sale_order, order, context=None):
        if(self._order_already_processed(cr,uid,order['orderId'],context)):
            return
        self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)

    def _create_sale_order_line_function(self, cr, uid, name, sale_order, order, context=None):
        stored_prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', order['productId'])], context=context)
        if(stored_prod_ids):
            prod_id = stored_prod_ids[0]
            prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)
            sale_order_line_obj = self.pool.get('sale.order.line')
            prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_id, sale_order, context=context)

            product_uom_qty = order['quantity']
            if(prod_lot != None and order['quantity'] > prod_lot.future_stock_forecast):
                product_uom_qty = prod_lot.future_stock_forecast

            sale_order_line = {
                'product_id': prod_id,
                'price_unit': prod_obj.list_price,
                'product_uom_qty': product_uom_qty,
                'product_uom': prod_obj.uom_id.id,
                'order_id': sale_order.id,
                'external_id':order['encounterId'],
                'external_order_id':order['orderId'],
                'name': prod_obj.name,
                'type': 'make_to_stock',
                'state': 'draft',
            }

            if prod_lot != None:
                life_date = prod_lot.life_date and datetime.strptime(prod_lot.life_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
                sale_order_line['price_unit'] = prod_lot.sale_price if prod_lot.sale_price > 0.0 else sale_order_line['price_unit']
                sale_order_line['batch_name'] = prod_lot.name
                sale_order_line['batch_id'] = prod_lot.id
                sale_order_line['expiry_date'] = life_date and life_date.strftime('%d/%m/%Y')

            sale_order_line_obj.create(cr, uid, sale_order_line, context=context)

            sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order.id, context=context)

            if product_uom_qty != order['quantity']:
                order['quantity'] = order['quantity'] - product_uom_qty
                self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)


    def _update_sale_order_line(self, cr, uid, name, sale_order, order, parent_order_line, context=None):
        self._delete_sale_order_line( cr, uid, parent_order_line, context=context)
        self._create_sale_order_line(cr, uid, name, sale_order, order, context=context)

    def _delete_sale_order_line(self, cr, uid, parent_order_line, context=None):
        if(parent_order_line):
            if(parent_order_line[0] and parent_order_line[0].order_id.state == 'draft'):
                self.pool.get('sale.order.line').unlink(cr, uid, [parent.id for parent in parent_order_line], context=context)

    def _fetch_parent(self, all_orders, child_order):
        for order in all_orders:
            if(order.get("orderId") == child_order.get("previousOrderId")):
                return order

    def _fetch_order_in_db(self, cr, uid, order_uuid, context=None):
        line_id = self.pool.get('sale.order.line').search(cr, uid, [('external_order_id', '=', order_uuid)], context=context)
        if(line_id):
            return self.pool.get('sale.order.line').browse(cr, uid, line_id, context=context)
        return None

    def _order_already_processed(self,cr,uid,order_uuid,context=None):
        return self.pool.get('processed.drug.order').search(cr, uid, [('order_uuid', '=', order_uuid)], context)

    def _process_orders(self, cr, uid, name, sale_order, all_orders, order, context=None):
        order_in_db = self._fetch_order_in_db(cr, uid, order['orderId'], context=context)

        if(order_in_db or self._order_already_processed(cr,uid, order['orderId'],context)):
            return

        parent_order_line = []
        if(order.get('previousOrderId', False)):
            parent_order = self._fetch_parent(all_orders, order)
            if(parent_order):
                self._process_orders(cr, uid, name, sale_order, all_orders, parent_order, context=None)
            parent_order_line = self._fetch_order_in_db(cr, uid, order['previousOrderId'], context=context)
            if(not parent_order_line and not self._order_already_processed(cr,uid, order['previousOrderId'],context)):
                raise osv.except_osv(('Error!'),("Previous order id does not exist in DB. This can be because of previous failed events"))

        if(order["voided"] or order.get('action', "") == "DISCONTINUE"):
            self._delete_sale_order_line(cr, uid, parent_order_line)
        elif(order.get('action', "") == "REVISE"):
            self._update_sale_order_line(cr, uid, name, sale_order, order, parent_order_line, context)
        else:

            self._create_sale_order_line(cr, uid, name, sale_order, order, context)

    def _create_sale_order(self, cr, uid, cus_id, name, shop_id, orders, context=None):
        sale_order = {
            'partner_id': cus_id,
            'name': name,
            'origin': 'ATOMFEED SYNC',
            'date_order': date.today(),
            'shop_id': shop_id,
            'partner_invoice_id': cus_id,
            'partner_shipping_id': cus_id,
            'order_policy': 'manual',
            'pricelist_id': 1,
        }
        if(orders):
            sale_order_id = self.pool.get('sale.order').create(cr, uid, sale_order, context=context)
            sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id, context=context)
            for order in orders:
                self._process_orders(cr, uid, name, sale_order, orders, order, context=context)


    def _update_sale_order(self, cr, uid, cus_id, name, shop_id, sale_order_id, orders, context=None):
        sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id)
        if(sale_order.state != 'draft'):
            raise osv.except_osv(('Error!'),("Sale order is already approved"))
        for order in orders:
            self._process_orders(cr, uid, name, sale_order, orders, order, context=context)

    def _get_openerp_orders(self, vals):
        if(not vals.get("orders", None)):
            return None
        orders_string = vals.get("orders")
        order_group = json.loads(orders_string)
        return order_group.get('openERPOrders', None)

    def _filter_processed_orders(self, context, cr, orders, uid):
        unprocessed_orders = []
        for order in orders:
            if (not self._order_already_processed(cr, uid, order['orderId'], context=context)):
                _logger.debug("The order %s is unprocessed. Adding it to the list",order['orderId'])
                unprocessed_orders.append(order)
        return self._filter_products_undefined(context,cr,unprocessed_orders,uid)

    def _filter_products_undefined(self,context,cr,orders,uid):
        products_in_system = []
        for order in orders:
            stored_prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', order['productId'])], context=context)
            if(stored_prod_ids):
                _logger.debug("The productId %s is available in the system. Adding it to the final list",order['productId'])
                products_in_system.append(order)
        return products_in_system

    def create_orders(self, cr,uid,vals,context):

        customer_id = vals.get("customer_id")
        location_name = vals.get("locationName")
        all_orders = self._get_openerp_orders(vals)
        if(not all_orders):
            return ""
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)
        if(customer_ids):
            cus_id = customer_ids[0]

            for orderType, ordersGroup in groupby(all_orders, lambda order: order.get('type')):
                orders = list(ordersGroup)
                unprocessed_orders = self._filter_processed_orders(context, cr, orders, uid)
                _logger.debug("unprocessed_order count is %s", unprocessed_orders)
                map_id_List = self.pool.get('order.type.shop.map').search(cr, uid, [('order_type', '=', orderType),('location_name', '=', location_name)], context=context)
                if(not map_id_List):
                    map_id_List = self.pool.get('order.type.shop.map').search(cr, uid, [('order_type', '=', orderType), ('location_name', '=', None)], context=context)
                if(map_id_List):
                    order_type_map = self.pool.get('order.type.shop.map').browse(cr, uid, map_id_List[0], context=context)
                    shop_id = order_type_map.shop_id.id

                    name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
                    sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', shop_id), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)
                    if(not sale_order_ids):
                        self._create_sale_order(cr, uid, cus_id, name, shop_id, unprocessed_orders, context)
                    else:
                        self._update_sale_order(cr, uid, cus_id, name, shop_id, sale_order_ids[0], unprocessed_orders, context)
        else:
            raise osv.except_osv(('Error!'), ("Patient Id not found in openerp"))