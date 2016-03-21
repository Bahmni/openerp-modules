import json
import logging

from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp import tools
from openerp.osv import fields, osv
from itertools import groupby
from datetime import date, datetime
from openerp.tools import pickle


_logger = logging.getLogger(__name__)


class order_save_service(osv.osv):
    _name = 'order.save.service'
    _auto = False

    def _create_sale_order_line(self, cr, uid, name, sale_order, order, context=None):
        if(self._order_already_processed(cr,uid,order['orderId'],order['dispensed'],context)):
            return
        self._create_sale_order_line_function(cr, uid, name, sale_order, order, context=context)

    def _get_product_ids(self, cr, uid, order, context=None):
        if order['productId']:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', order['productId'])], context=context)
        else:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('name_template', '=', order['conceptName'])], context=context)

        return prod_ids


    def _create_sale_order_line_function(self, cr, uid, name, sale_order, order, context=None):

        stored_prod_ids = self._get_product_ids(cr, uid, order, context=context)

        if(stored_prod_ids):
            prod_id = stored_prod_ids[0]
            prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)
            sale_order_line_obj = self.pool.get('sale.order.line')
            prod_lot = sale_order_line_obj.get_available_batch_details(cr, uid, prod_id, sale_order, context=context)

            actual_quantity = order['quantity']
            comments = " ".join([str(actual_quantity), str(order.get('quantityUnits', None))])

            default_quantity_object = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'bahmni_sale_discount', 'group_default_quantity')[1]
            default_quantity_total = self.pool.get('res.groups').browse(cr, uid, default_quantity_object, context=context)
            default_quantity_value = 1
            if default_quantity_total and len(default_quantity_total.users) > 0:
                default_quantity_value = -1

            order['quantity'] = self._get_order_quantity(cr, uid, order, default_quantity_value)
            product_uom_qty = order['quantity']
            if(prod_lot != None and order['quantity'] > prod_lot.future_stock_forecast):
                product_uom_qty = prod_lot.future_stock_forecast

            sale_order_line = {
                'product_id': prod_id,
                'price_unit': prod_obj.list_price,
                'comments': comments,
                'product_uom_qty': product_uom_qty,
                'product_uom': prod_obj.uom_id.id,
                'order_id': sale_order.id,
                'external_id':order['encounterId'],
                'external_order_id':order['orderId'],
                'name': prod_obj.name,
                'type': 'make_to_stock',
                'state': 'draft',
                'dispensed_status': order['dispensed']

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

    def _get_order_quantity(self, cr, uid, order, default_quantity_value):
        if(not self.pool.get('syncable.units').search(cr, uid, [('name', '=', order['quantityUnits'])])):
            return default_quantity_value
        return order['quantity']


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

    def _order_already_processed(self,cr,uid,order_uuid, dispensed_status, context=None):
        processed_drug_order_id = self.pool.get('processed.drug.order').search(cr, uid, [('order_uuid', '=', order_uuid), ('dispensed_status', '=', dispensed_status)], context)
        return processed_drug_order_id

    def _process_orders(self, cr, uid, name, sale_order, all_orders, order, context=None):

        order_in_db = self._fetch_order_in_db(cr, uid, order['orderId'], context=context)

        if(order_in_db or self._order_already_processed(cr,uid, order['orderId'], order['dispensed'],context)):
            return

        parent_order_line = []
        # if(order.get('previousOrderId', False) and order.get('dispensed', "") == "true"):
        #     self._create_sale_order_line(cr, uid, name, sale_order, order, context)

        if(order.get('previousOrderId', False) and order.get('dispensed', "") == "false"):
            parent_order = self._fetch_parent(all_orders, order)
            if(parent_order):
                self._process_orders(cr, uid, name, sale_order, all_orders, parent_order, context=None)
            parent_order_line = self._fetch_order_in_db(cr, uid, order['previousOrderId'], context=context)
            if(not parent_order_line and not self._order_already_processed(cr,uid, order['previousOrderId'], order['dispensed'], context)):
                raise osv.except_osv(('Error!'),("Previous order id does not exist in DB. This can be because of previous failed events"))

        if(order["voided"] or order.get('action', "") == "DISCONTINUE"):
            self._delete_sale_order_line(cr, uid, parent_order_line)
        elif(order.get('action', "") == "REVISE" and order.get('dispensed', "") == "false"):
            self._update_sale_order_line(cr, uid, name, sale_order, order, parent_order_line, context)
        else:
            self._create_sale_order_line(cr, uid, name, sale_order, order, context)

    def _create_sale_order(self, cr, uid, cus_id, name, shop_id, orders, care_setting, provider_name, context=None):
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
            'care_setting' : care_setting,
            'provider_name' : provider_name
        }
        if(orders):
            sale_order_id = self.pool.get('sale.order').create(cr, uid, sale_order, context=context)
            sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id, context=context)
            for order in orders:
                self._process_orders(cr, uid, name, sale_order, orders, order, context=context)


    def _update_sale_order(self, cr, uid, cus_id, name, shop_id, care_setting,  sale_order_id, orders, provider_name, context=None):

        sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id)
        sale_order.write({'care_setting': care_setting})
        sale_order.write({'provider_name': provider_name})


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
            if (not self._order_already_processed(cr, uid, order['orderId'], order['dispensed'], context=context)):
                unprocessed_orders.append(order)
        return self._filter_products_undefined(context,cr,unprocessed_orders,uid)

    def _filter_products_undefined(self,context,cr,orders,uid):
        products_in_system = []

        for order in orders:
            stored_prod_ids = self._get_product_ids(cr, uid, order, context=context)
            if(stored_prod_ids):
                products_in_system.append(order)
        return products_in_system

    def _remove_existing_sale_order_line(self, cr, uid, sale_order_id, unprocessed_dispensed_order, context):
        sale_order_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_id)], context=context)
        sale_order_lines = self.pool.get('sale.order.line').browse(cr, uid, sale_order_line_ids, context=context)
        sale_order_lines_to_be_saved = []
        for order in unprocessed_dispensed_order:
            for sale_order_line in sale_order_lines:
                if(order['orderId'] == sale_order_line['external_order_id']):
                    if(order['dispensed'] != sale_order_line['dispensed_status']):
                        sale_order_line_to_be_saved = self.pool.get('sale.order.line').browse(cr, uid, sale_order_line['id'], context=context)
                        sale_order_lines_to_be_saved.append(sale_order_line_to_be_saved)

        self.pool.get('sale.order.line').unlink(cr, uid, [sale_order_line_to_be_saved.id for sale_order_line_to_be_saved in sale_order_lines_to_be_saved], context=context)

    def _get_default_value_of_convert_dispensed (self,cr,uid):
        search_criteria = [
            ('key', '=', 'default'),
            ('model', '=', 'sale.config.settings'),
            ('name', '=', 'convert_dispensed'),
            ]
        ir_values_obj = self.pool.get('ir.values')
        defaults = ir_values_obj.browse(cr, uid, ir_values_obj.search(cr, uid, search_criteria))
        default_convert_dispensed = pickle.loads(defaults[0].value.encode('utf-8'))
        return default_convert_dispensed


    def _get_shop_and_local_shop_id (self, cr, uid, orderType, location_name, context):
        shop_list = self.pool.get('order.type.shop.map').search(cr, uid, [], context = context)
        shop_list_with_orderType = self.pool.get('order.type.shop.map').search(cr, uid, [('order_type', '=', orderType)], context=context)
        if(len(shop_list) == 0):  ##Checks if the order type to shop mapping table is empty or not, if empty then pick the first shop in the sale_shop list
            shop_id_list = self.pool.get('sale.shop').search(cr, uid,[], context=context)
            shop_id = self.pool.get('sale.shop').browse(cr, uid, shop_id_list[0], context=context).id
            local_shop_id = False
        elif(len(shop_list_with_orderType) == 0): ##orderType to shop mapping table may not be empty, but it may not contain the orderType that is sent
            first_mapping_id = shop_list[0]
            first_mapping_obj = self.pool.get('order.type.shop.map').browse(cr, uid, first_mapping_id, context=context)
            shop_id = first_mapping_obj.shop_id.id

            if(not first_mapping_obj.local_shop_id):
                local_shop_id = False
            else:
                local_shop_id = first_mapping_obj.local_shop_id.id
        else: ##orderType to shop mapping table is not empty and has a mapping of the orderType that is sent //general scenario
            shop_mapping_with_locations = self.pool.get('order.type.shop.map').search(cr, uid, [('order_type', '=', orderType), ('location_name', '=', location_name)], context=context)
            if(not shop_mapping_with_locations):
                shop_mapping_with_locations = self.pool.get('order.type.shop.map').search(cr, uid, [('order_type', '=', orderType), ('location_name', '=', None)], context=context)
            if(shop_mapping_with_locations):
                order_type_map = self.pool.get('order.type.shop.map').browse(cr, uid, shop_mapping_with_locations[0], context=context)
                shop_id = order_type_map.shop_id.id
                local_shop_id = order_type_map.local_shop_id.id

        return (shop_id, local_shop_id)

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
                care_setting = orders[0].get('visitType').lower()
                provider_name = orders[0].get('providerName')
                unprocessed_orders = self._filter_processed_orders(context, cr, orders, uid)

                tup = self._get_shop_and_local_shop_id(cr, uid, orderType, location_name, context)
                shop_id = tup[0]
                local_shop_id = tup[1]

                name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
                #Adding both the ids to the unprocessed array of orders, Separating to dispensed and non-dispensed orders
                unprocessed_dispensed_order = []
                unprocessed_non_dispensed_order = []
                for unprocessed_order in unprocessed_orders :
                    unprocessed_order['custom_shop_id'] = shop_id
                    unprocessed_order['custom_local_shop_id'] = local_shop_id
                    if(unprocessed_order['dispensed'] == 'true') :
                        unprocessed_dispensed_order.append(unprocessed_order)
                    else :
                        unprocessed_non_dispensed_order.append(unprocessed_order)

                if(len(unprocessed_non_dispensed_order) > 0 ) :
                    sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_non_dispensed_order[0]['custom_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    if(not sale_order_ids):
                        #Non Dispensed New
                        self._create_sale_order(cr, uid, cus_id, name, unprocessed_non_dispensed_order[0]['custom_shop_id'], unprocessed_non_dispensed_order, care_setting, provider_name, context)
                    else:
                        #Non Dispensed Update
                        self._update_sale_order(cr, uid, cus_id, name, unprocessed_non_dispensed_order[0]['custom_shop_id'], care_setting, sale_order_ids[0], unprocessed_non_dispensed_order, provider_name, context)

                    sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_non_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    if(len(sale_order_ids_for_dispensed) > 0):
                        if(sale_order_ids_for_dispensed[0]) :
                            sale_order_line_ids_for_dispensed = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids_for_dispensed[0])], context=context)
                            if(len(sale_order_line_ids_for_dispensed) == 0):
                                self.pool.get('sale.order').unlink(cr, uid, sale_order_ids_for_dispensed, context=context)


                if(len(unprocessed_dispensed_order) > 0 and local_shop_id) :
                    sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)

                    if(not sale_order_ids_for_dispensed):
                        #Remove existing sale order line
                        self._remove_existing_sale_order_line(cr,uid,sale_order_ids[0],unprocessed_dispensed_order,context=context)

                        #Removing existing empty sale order
                        sale_order_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids[0])], context=context)

                        if(len(sale_order_line_ids) == 0):
                            self.pool.get('sale.order').unlink(cr, uid, sale_order_ids, context=context)

                        #Dispensed New
                        self._create_sale_order(cr, uid, cus_id, name, unprocessed_dispensed_order[0]['custom_local_shop_id'], unprocessed_dispensed_order, care_setting, provider_name, context)

                        if(self._get_default_value_of_convert_dispensed (cr,uid)):
                            sale_order_ids_for_dispensed = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('shop_id', '=', unprocessed_dispensed_order[0]['custom_local_shop_id']), ('state', '=', 'draft'), ('origin', '=', 'ATOMFEED SYNC')], context=context)
                            self.pool.get('sale.order').action_button_confirm(cr, uid, sale_order_ids_for_dispensed, context)

                    else:
                        #Remove existing sale order line
                        self._remove_existing_sale_order_line(cr,uid,sale_order_ids[0],unprocessed_dispensed_order,context=context)

                        #Removing existing empty sale order
                        sale_order_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_ids[0])], context=context)
                        if(len(sale_order_line_ids) == 0):
                            self.pool.get('sale.order').unlink(cr, uid, sale_order_ids, context=context)

                        #Dispensed Update
                        self._update_sale_order(cr, uid, cus_id, name, unprocessed_dispensed_order[0]['custom_local_shop_id'], care_setting, sale_order_ids_for_dispensed[0], unprocessed_dispensed_order, provider_name, context)
        else:
            raise osv.except_osv(('Error!'), ("Patient Id not found in openerp"))