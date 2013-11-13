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
        village = vals.get("village")
        customer = {'ref': ref, 'name': name, 'village': village}
        return customer

    def _create_sale_orderline(self,cr,uid,name, product_ids, so,  uom_obj,external_order_line_id,context):
        for prod_id in product_ids:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', prod_id)], context=context)
            if(len(prod_ids) > 0):
                prod_id = prod_ids[0]
                prod_obj = self.pool.get('product.product').browse(cr, uid, prod_id)

                sale_order_line = {'product_id': prod_id, 'price_unit': prod_obj.list_price, 'product_uom_qty': 1,
                                   'product_uom': uom_obj, 'order_id': so,
                                   'name': name, 'type': 'make_to_stock', 'state': 'draft', 'product_dosage': '0',
                                   'product_number_of_days': '0','external_id':external_order_line_id}
                self.pool.get('sale.order.line').create(cr, uid, sale_order_line, context=context)

    def _create_sale_order(self, context, cr, cus_id, name, external_id, orders, shop_id, uid, uom_obj,external_order_line_id):
        order = orders[0]
        sale_order_group = {'group_id': order['visitId'], 'description': order['description'], 'type': order['type'] }

        sale_order_group_ids = self.pool.get('visit').search(cr, uid, [('group_id', '=', order['visitId'])], context=context)
        if(len(sale_order_group_ids) == 0):
            sog_id = self.pool.get('visit').create(cr, uid, sale_order_group, context=context)
        else:
            sog_id = sale_order_group_ids[0]

        sale_order = {'partner_id': cus_id, 'name': name, 'date': datetime.date.today(), 'shop_id': shop_id,
                      'partner_invoice_id': cus_id, 'partner_shipping_id': cus_id,
                      'order_policy': 'manual', 'pricelist_id': 1, 'external_id': external_id, 'group_id': sog_id }
        so_id = self.pool.get('sale.order').create(cr, uid, sale_order, context=context)

        group_prod_ids = []
        for order in orders:
            group_prod_ids = group_prod_ids + order['productIds']
        self._create_sale_orderline(cr,uid,name, group_prod_ids, so_id, uom_obj,external_order_line_id,context)

    def _update_sale_order(self, context, cr, uid, cus_id, name, external_id,shop_id, uom_obj,order_id,group_prod_ids,external_order_line_id):
        sale_order = self.pool.get('sale.order').browse(cr,uid,order_id)
        if(sale_order.state != 'draft'):
            raise osv.except_osv(('Error!'),("Sale order is already approved"))

        for order_line in sale_order.order_line :
            prod_obj = order_line.product_id
            ids = [order_line.id]
            if prod_obj.uuid in group_prod_ids:
                group_prod_ids.remove(prod_obj.uuid)
            else :
                self.pool.get('sale.order.line').unlink(cr,uid,ids)

        self._create_sale_orderline(cr,uid,name, group_prod_ids, sale_order.id, uom_obj,external_order_line_id,context)


    def _create_orders(self, cr,uid,vals,context):
        customer_id = vals.get("customer_id")
        orders_string = vals.get("orders")
        order_group = json.loads(orders_string)
        order_group_id = order_group.get('id')
        orders = order_group.get('openERPOrders')
        group_prod_ids = []

        for order in orders:
            group_prod_ids = group_prod_ids + order['productIds']

        external_order_line_id = order.get('id')
        uom_obj = self.pool.get('product.uom').search(cr, uid, [('name', '=', 'Unit(s)')], context=context)[0]
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)


        if(len(customer_ids) > 0):
            cus_id = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)[0]
            shop_id = self.pool.get('sale.shop').search(cr, uid, [('name', '=', 'Pharmacy')], context=context)[0]
            name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
            sale_order_ids = self.pool.get('sale.order').search(cr, uid, [('external_id', '=', order_group_id)], context=context)
            if(len(sale_order_ids) == 0) :
                self._create_sale_order(context, cr, cus_id, name, order_group_id,orders,shop_id, uid, uom_obj,external_order_line_id)
            else:
                self._update_sale_order(context, cr,  uid,cus_id, name, order_group_id,shop_id, uom_obj,sale_order_ids[0],group_prod_ids,external_order_line_id)
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

        marker_ids = self.pool.get('atom.feed.marker').search(cr, uid, [('feed_uri', '=', feed_uri)], limit=1)
        if "$param.name" in feed_uri_for_last_read_entry or "$param.name" in feed_uri :
            raise osv.except_osv(('Error!'),("Patient Id not found in openerp"))

        if len(marker_ids) > 0:
            self._update_marker(cr, feed_uri_for_last_read_entry, last_read_entry_id, marker_ids, uid)
        else:
            self._create_marker(cr, feed_uri_for_last_read_entry, last_read_entry_id, uid,feed_uri)

    def _create_or_update_customer(self,cr, patient_ref, uid, vals,context):
        customer = self._create_customer(vals)
        existing_customer_ids = self.pool.get('res.partner').search(cr, uid, [('ref', '=', patient_ref)])
        if len(existing_customer_ids) > 0:
            self.pool.get('res.partner').write(cr, uid, existing_customer_ids[0], customer, context=context)
        else:
            self.pool.get('res.partner').create(cr, uid, customer, context=context)

    def process_event(self, cr, uid, vals,context=None):
        _logger.info("vals")
        _logger.info(vals)
        category = vals.get("category")
        patient_ref = vals.get("ref")
        if(category == "create.customer"):
            self._create_or_update_customer( cr, patient_ref, uid, vals,context)
        if(category == "create.sale.order"):
            sale_order  = self._create_orders(cr,uid,vals,context)
        self._create_or_update_marker(cr, uid, vals)
        return {'success': True}

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
        'external_id'   : fields.char('external_id', size=64),
        'group_id'      : fields.many2one('visit', 'Group Reference', required=False, select=True, readonly=True),
        'group_description':fields.related('group_id', 'description', type='char', string='Visit'),
        }

class sale_order_group(osv.osv):
    _name = "visit"
    _table = "sale_order_group"

    def __str__(self):
        return "Visit"

    _columns = {
        'group_id'      : fields.char('group_id', 38),
        'description'   : fields.char('visit', 40),
        'type'          : fields.char('type', 15)
    }


class sale_order_line(osv.osv):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    _columns = {
        'external_id': fields.char('external_id', size=64),
    }

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