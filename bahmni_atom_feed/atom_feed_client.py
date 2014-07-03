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

    def _create_sale_orderline(self,cr,uid,name, product_id, so,  uom_obj,external_order_line_id,context):
            stored_prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', product_id)], context=context)
            if(len(stored_prod_ids) > 0):
                prod_id = stored_prod_ids[0]
                prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)

                sale_order_line = {'product_id': prod_id, 'price_unit': prod_obj.list_price, 'product_uom_qty': 1,
                                   'product_uom': uom_obj, 'order_id': so,
                                   'name': name, 'type': 'make_to_stock', 'state': 'draft', 'product_dosage': '0',
                                   'product_number_of_days': '0','external_id':external_order_line_id}
                self.pool.get('sale.order.line').create(cr, uid, sale_order_line, context=context)

    def _create_sale_order(self, context, cr, cus_id, name, external_id, orders, shop_id, uid, uom_obj):
        order = orders[0]
        sale_order_group = {'group_id': order['visitId'], 'description': order['description'], 'type': order['type'] }

        sale_order_group_ids = self.pool.get('visit').search(cr, uid, [('group_id', '=', order['visitId'])], context=context)
        if(len(sale_order_group_ids) == 0):
            sog_id = self.pool.get('visit').create(cr, uid, sale_order_group, context=context)
        else:
            sog_id = sale_order_group_ids[0]

        sale_order = {'partner_id': cus_id, 'name': name, 'date': datetime.date.today(), 'shop_id': shop_id,
                      'partner_invoice_id': cus_id, 'partner_shipping_id': cus_id,
                      'order_policy': 'manual', 'pricelist_id': 1, 'external_id': external_id, 'group_id': sog_id,'group_description':order['description'] }

        if(len(orders) > 0):
            so_id = self.pool.get('sale.order').create(cr, uid, sale_order, context=context)
            for order in orders:
                if(len(order['productIds']) > 0):
                    self._create_sale_orderline(cr,uid,name, order['productIds'][0], so_id, uom_obj,order.get('id'),context)

    def _update_sale_order(self, context, cr, uid, cus_id, name, external_id,shop_id, uom_obj,order_id,orders):
        prod_order_Map ={}
        group_prod_ids = []
        deleted_prod_ids = []

        for order in orders:
            if(order["voided"]):
                deleted_prod_ids += order['productIds']
            else:
                group_prod_ids = group_prod_ids + order['productIds']
                for prodId in order['productIds']:
                    prod_order_Map[prodId] = order.get('id')

        sale_order = self.pool.get('sale.order').browse(cr,uid,order_id)
        if(sale_order.state != 'draft'):
            raise osv.except_osv(('Error!'),("Sale order is already approved"))

        for order_line in sale_order.order_line :
            prod_obj = order_line.product_id
            ids = [order_line.id]
            if prod_obj.uuid in group_prod_ids:
                group_prod_ids.remove(prod_obj.uuid)
            else :
                if prod_obj.uuid in deleted_prod_ids:
                    self.pool.get('sale.order.line').unlink(cr,uid,ids)

        for prod_id in group_prod_ids:
            self._create_sale_orderline(cr,uid,name, prod_id, sale_order.id, uom_obj,prod_order_Map[prod_id],context)


    def _create_orders(self, cr,uid,vals,context):
        customer_id = vals.get("customer_id")
        if(vals.get("orders")==None): 
            return ""

        orders_string = vals.get("orders")
        order_group = json.loads(orders_string)
        order_group_id = order_group.get('id')
        orders = order_group.get('openERPOrders')
        if(len(orders) == 0):
            return ""

        group_prod_ids = []

        uom_obj = self.pool.get('product.uom').search(cr, uid, [('name', '=', 'Unit(s)')], context=context)[0]
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)

        if(len(customer_ids) > 0):
            cus_id = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)[0]
            shop_id = self.pool.get('sale.shop').search(cr, uid, [('name', '=', 'Pharmacy')], context=context)[0]
            name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
            sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('external_id', '=', order_group_id)], context=context)
            if(len(sale_order_ids) == 0) :
                self._create_sale_order(context, cr, cus_id, name, order_group_id,orders,shop_id, uid, uom_obj)
            else:
                self._update_sale_order(context, cr,  uid,cus_id, name, order_group_id,shop_id, uom_obj,sale_order_ids[0],orders)
        else:
            raise osv.except_osv(('Error!'),("Patient Id not found in openerp"))

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