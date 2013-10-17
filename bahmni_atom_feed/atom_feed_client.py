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

    def _create_sale_order(self, cr,uid,vals,context):
        customer_id = vals.get("customer_id")
        date = vals.get("date")
        product_ids_string = vals.get("product_ids")
        product_ids = product_ids_string.split(',')

        uom_obj = self.pool.get('product.uom').search(cr, uid, [('name', '=', 'Unit(s)')], context=context)[0]
        cus_id = self.pool.get('res.partner').search(cr, uid, [('ref', '=', customer_id)], context=context)[0]
        shop_id = self.pool.get('sale.shop').search(cr, uid, [('name', '=', 'Pharmacy')], context=context)[0]

        name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
        sale_order = {'partner_id': cus_id, 'name': name, 'date': datetime.date.today(),'shop_id':shop_id,'partner_invoice_id':cus_id,'partner_shipping_id':cus_id,
                      'order_policy':'manual','pricelist_id':1}
        so = self.pool.get('sale.order').create(cr, uid, sale_order, context=context)

        for prod_id in product_ids:
            prod_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', prod_id)], context=context)
            if(len(prod_ids) > 0):
                prod_id = prod_ids[0]
                prod_obj = self.pool.get('product.product').browse(cr,uid,prod_id)

                sale_order_line = {'product_id':prod_id,'price_unit':prod_obj.list_price,'product_uom_qty':1,'product_uom':uom_obj,'order_id':so,
                                   'name':name,'type':'make_to_stock','state':'draft','product_dosage':'0','product_number_of_days':'0'}
                self.pool.get('sale.order.line').create(cr, uid, sale_order_line, context=context)

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
        _logger.info(vals)
        category = vals.get("category")
        patient_ref = vals.get("ref")
        if(category == "create.customer"):
            self._create_or_update_customer( cr, patient_ref, uid, vals,context)
        if(category == "create.sale.order"):
            sale_order  = self._create_sale_order(cr,uid,vals,context)
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