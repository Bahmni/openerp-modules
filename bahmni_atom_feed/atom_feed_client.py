from datetime import datetime
import json
import uuid
from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv
import logging
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

    def process_event(self, cr, uid, vals,context=None):
        category = vals.get("category")
        if(category == "create.customer"):
            customer = self._create_customer(vals)
            self.pool.get('res.partner').create(cr, uid, customer, context=context)
            self._create_or_update_marker(cr, uid, vals)


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