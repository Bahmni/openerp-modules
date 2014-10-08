from datetime import datetime
import json
import uuid
from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv
import logging
import datetime
_logger = logging.getLogger(__name__)

class atom_event_worker(osv.osv):
    _name = 'atom.event.worker'
    _auto = False

    def _create_customer(self, vals):
        ref = vals.get("ref")
        name = vals.get("name")
        local_name = vals.get("local_name")
        village = vals.get("village")
        customer = {'ref': ref, 'name': name, 'local_name': local_name, 'village': village}
        return customer

    def _find_sale_order_line_for_product(self, cr, uid, sale_order, product_uuid, context=None):
        line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order.id)], context=context)
        for line in self.pool.get('sale.order.line').browse(cr, uid, line_ids):
            if(line.product_id.uuid == product_uuid):
                return line
        return None

    def _create_sale_order_line(self, cr, uid, name, sale_order, order, context=None):
        if(self._find_sale_order_line_for_product(cr, uid, sale_order, order.get('productId', None), context)):
            return
        stored_prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', order['productId'])], context=context)
        uom_obj = self.pool.get('product.uom').search(cr, uid, [('name', '=', 'Unit(s)')], context=context)[0]
        if(stored_prod_ids):
            prod_id = stored_prod_ids[0]
            prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)
            sale_order_line = {
                'product_id': prod_id,
                'price_unit': prod_obj.list_price,
                'product_uom_qty': order['quantity'],
                'product_uom': uom_obj,
                'order_id': sale_order.id,
                'external_id':order['encounterId'],
                'name': name,
                'type': 'make_to_stock',
                'state': 'draft',
            }
            self.pool.get('sale.order.line').create(cr, uid, sale_order_line, context=context)

    def _update_sale_order_line(self, cr, uid, name, sale_order, order, context=None):
        uom_obj = self.pool.get('product.uom').search(cr, uid, [('name', '=', 'Unit(s)')], context=context)[0]
        update_dict = {
            'product_uom_qty': order.get('quantity', 0),
            'product_uom': uom_obj,
        }
        line = self._find_sale_order_line_for_product(cr, uid, sale_order, order.get('productId', None), context)
        if(line):
            self.pool.get('sale.order.line').write(cr, uid, line.id, update_dict, context=context)
        else:
            self._create_sale_order_line(cr, uid, name, sale_order, order, context=context)

    def _delete_sale_order_line(self, cr, uid, sale_order, order, context=None):
        line = self._find_sale_order_line_for_product(cr, uid, sale_order, order.get('productId', None), context)
        if(line):
            self.pool.get('sale.order.line').unlink(cr, uid, [line.id], context=context)

    def _fetch_parent(self, all_orders, child_order):
        for order in all_orders:
            if(order.get("orderId") == child_order.get("previousOrderId")):
                return order

    def _process_orders(self, cr, uid, name, sale_order, all_orders, order, processed_orders=[], context=None):
        if(order in processed_orders):
            return

        parent_order = self._fetch_parent(all_orders, order)
        if(parent_order):
            self._process_orders(cr, uid, name, sale_order, all_orders, parent_order, processed_orders, context=None)

        if(order["voided"] or order.get('action', "") == "DISCONTINUE"):
            self._delete_sale_order_line(cr, uid, sale_order, order, context)
        elif(order.get('action', "") == "REVISE"):
            self._update_sale_order_line(cr, uid, name, sale_order, order, context)
        else:
            self._create_sale_order_line(cr, uid, name, sale_order, order, context)
        processed_orders.append(order)

    def _create_sale_order(self, cr, uid, cus_id, name, shop_id, orders, context=None):
        sale_order = {
            'partner_id': cus_id,
            'name': name,
            'date': datetime.date.today(),
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
        prod_order_Map ={}
        deleted_prod_ids = []
        updated_prod_map = {}
        sale_order = self.pool.get('sale.order').browse(cr, uid, sale_order_id)
        if(sale_order.state != 'draft'):
            raise osv.except_osv(('Error!'),("Sale order is already approved"))
        for order in orders:
            self._process_orders(cr, uid, name, sale_order, orders, order, context=context)

    def _create_orders(self, cr,uid,vals,context):
        customer_id = vals.get("customer_id")
        orders = self._get_openerp_orders(vals)
        if(not orders):
            return ""
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)
        if(customer_ids):
            cus_id = customer_ids[0]
            shop_id = self.pool.get('sale.shop').search(cr, uid, [('name', '=', 'Pharmacy')], context=context)[0]
            name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
            sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', cus_id), ('state', '=', 'draft')], context=context)
            if(not sale_order_ids):
                self._create_sale_order(cr, uid, cus_id, name, shop_id, orders, context)
            else:
                self._update_sale_order(cr, uid, cus_id, name, shop_id, sale_order_ids[0], orders, context)
        else:
            raise osv.except_osv(('Error!'), ("Patient Id not found in openerp"))

    def _get_openerp_orders(self, vals):
        if(not vals.get("orders", None)):
            return None
        orders_string = vals.get("orders")
        order_group = json.loads(orders_string)
        return order_group.get('openERPOrders', None)

    def _update_marker(self, cr, feed_uri_for_last_read_entry, last_read_entry_id, marker_ids, uid):
        for marker_id in marker_ids:
            marker = self.pool.get('atom.feed.marker')
            marker._update_marker(cr,uid,marker_id,last_read_entry_id, feed_uri_for_last_read_entry)

    def _create_marker(self, cr, feed_uri_for_last_read_entry, last_read_entry_id, uid,feed_uri):
        marker = {'feed_uri': feed_uri, 'last_read_entry_id': last_read_entry_id,
                  'feed_uri_for_last_read_entry': feed_uri_for_last_read_entry}
        self.pool.get('atom.feed.marker').create(cr, uid, marker)

    def _create_or_update_marker(self, cr, uid, vals):
        is_failed_event = vals.get('is_failed_event',False)
        if(is_failed_event): return

        last_read_entry_id = vals.get('last_read_entry_id')
        feed_uri_for_last_read_entry = vals.get('feed_uri_for_last_read_entry')
        feed_uri = vals.get('feed_uri')

        # Rohan/Mujir - do not update markers for failed events (failed events have empty 'feed_uri_for_last_read_entry')
        if "$param" in feed_uri_for_last_read_entry or "$param" in feed_uri or feed_uri_for_last_read_entry == None or not feed_uri_for_last_read_entry:
            return

        marker_ids = self.pool.get('atom.feed.marker').search(cr, uid, [('feed_uri', '=', feed_uri)], limit=1)

        if len(marker_ids) > 0:
            self._update_marker(cr, feed_uri_for_last_read_entry, last_read_entry_id, marker_ids, uid)
        else:
            self._create_marker(cr, feed_uri_for_last_read_entry, last_read_entry_id, uid,feed_uri)

    def _create_or_update_customer(self,cr, patient_ref, uid, vals,context):
        customer = self._create_customer(vals)
        existing_customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', patient_ref)])
        if len(existing_customer_ids) > 0:
            self.pool.get('res.partner').write(cr, uid, existing_customer_ids[0], customer, context=context)
            self._create_or_update_person_attributes(cr, uid, existing_customer_ids[0], vals, context=context)
            self._create_or_update_person_address(cr, uid, existing_customer_ids[0], vals, context=context)
        else:
            cust_id = self.pool.get('res.partner').create(cr, uid, customer, context=context)
            self._create_or_update_person_attributes(cr, uid, cust_id, vals, context=context)
            self._create_or_update_person_address(cr, uid, cust_id, vals, context=context)


    def _create_or_update_person_attributes(self, cr, uid, cust_id, vals, context=None):
        attributes = json.loads(vals.get("attributes", "{}"))
        for key in attributes:
            attribute_id = self.pool.get('res.partner.attributes').search(cr, uid, [('name', '=', key), ('partner_id' , '=', cust_id)]) 
            column_dict = {'name': key, 'value': attributes[key], 'partner_id': cust_id}
            if len(attribute_id) > 0:
                self.pool.get('res.partner.attributes').write(cr, uid, attribute_id, column_dict, context=context)    
            else:
                self.pool.get('res.partner.attributes').create(cr, uid, column_dict, context=context)


    def _create_or_update_person_address(self, cr, uid, cust_id, vals, context=None):
        try:
            address = json.loads(vals.get("preferredAddress", "{}"))
        except ValueError:
            raise ValueError("Could not retrive preferred address from the String - %s" % str(vals))
        existing_address = self.pool.get('res.partner.address').search(cr, uid, [('partner_id' , '=', cust_id)])
        if not address and not existing_address:
            return
        column_dict = {
            'address1': address['address1'],
            'address2': address['address2'],
            'city_village': address['cityVillage'],
            'state_province': address['stateProvince'],
            'country': address['country'],
            'county_district': address['countyDistrict'],
            'address3': address['address3'],
            'partner_id': cust_id
        }
        if len(existing_address) > 0:
            self.pool.get('res.partner.address').write(cr, uid, existing_address, column_dict, context=context)
        else:
            self.pool.get('res.partner.address').create(cr, uid, column_dict, context=context)


    def process_event(self, cr, uid, vals,context=None):
        _logger.info("vals")
        _logger.info(vals)
        category = vals.get("category")
        patient_ref = vals.get("ref")
        if(category == "create.customer"):
            self._create_or_update_customer( cr, patient_ref, uid, vals,context)
        if(category == "create.sale.order"):
            sale_order  = self._create_orders(cr,uid,vals,context)
        if(category == "create.lab.test"):
            self.pool.get('lab.test.service').create_or_update_labtest(cr,uid,vals,context)
        if(category == "create.drug"):
            self.pool.get('drug.service').create_or_update_drug(cr,uid,vals,context)
        if(category == "create.drug.category"):
            self.pool.get('drug.service').create_or_update_drug_category(cr,uid,vals,context)
        if(category == "create.drug.uom"):
            self.pool.get('product.uom.service').create_or_update_product_uom(cr,uid,vals,context)
        if(category == "create.drug.uom.category"):
            self.pool.get('product.uom.service').create_or_update_product_uom_category(cr,uid,vals,context)

        self._create_or_update_marker(cr, uid, vals)
        return {'success': True}


class atom_feed_marker(osv.osv):
    _name = 'atom.feed.marker'
    _table = 'markers'

    def _update_marker(self,cr,uid,marker_id,last_read_entry_id,feed_uri_for_last_read_entry):
#        marker = self.pool.get('atom.feed.marker').browse(marker_id)
        self.write(cr, uid, marker_id, {'last_read_entry_id': last_read_entry_id,'feed_uri_for_last_read_entry': feed_uri_for_last_read_entry,})


    _columns ={
        'feed_uri':fields.char("uuid", size=250, translate=True, required=True),
        'last_read_entry_id':fields.char("Title", size=250, translate=True, required=True),
        'feed_uri_for_last_read_entry':fields.char("Category", size=100, translate=True, required=True),
        }