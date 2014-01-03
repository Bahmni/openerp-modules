from datetime import datetime
import json
import uuid
from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class atom_event_publisher(osv.osv):
    _name = 'event.publisher'
    _auto = False

    def publish_event(self, cr, uid, category, obj):
        serializedContents = json.dumps(obj)
        event_vals = {
            'uuid': uuid.uuid4(),
            'category': category,
            'title': obj.get('id','Null'),
            'timestamp': datetime.now(),
            'uri': None,
            'object': serializedContents,
        }
        event_obj = self.pool.get('event.records')
        event_obj.create(cr, uid, event_vals)



class atom_event(osv.osv):
    _name = 'event.records'
    _table = 'event_records'

    _columns={
        'uuid':fields.char("uuid", size=250, translate=True, required=True),
        'title':fields.char("Title", size=250, translate=True, required=True),
        'category':fields.char("Category", size=100, translate=True, required=True),
        'timestamp':fields.datetime("Time of event creation", required=True),
        'uri':fields.char("URI", size=250, translate=True,),
        'object':fields.text("serializedContents", required=True),
    }
