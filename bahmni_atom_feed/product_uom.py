import json
import logging

from dateutil.relativedelta import relativedelta
import uuid
from osv import fields, osv
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_uom(osv.osv):

    _name = 'product.uom'
    _inherit = 'product.uom'

    def create(self, cr, uid, data, context=None):
        if data.get("uuid") is None:
            data['uuid'] = str(uuid.uuid4())

        prod_id = super(product_uom, self).create(cr, uid, data, context)

        return prod_id


    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom()

class product_uom_categ(osv.osv):

    _name = 'product.uom.categ'
    _inherit = 'product.uom.categ'

    def create(self, cr, uid, data, context=None):
        if data.get("uuid") is None:
            data['uuid'] = str(uuid.uuid4())

        prod_id = super(product_uom_categ, self).create(cr, uid, data, context)
        return prod_id

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom_categ()


class product_uom_service(osv.osv):
    _name = 'product.uom.service'
    _auto = False

    def create_or_update_product_uom(self,cr, uid, vals, context=None):
        product_uom = json.loads(vals.get("product_uom"))
        object_ids = self.pool.get("product.uom").search(cr, uid, [('uuid', '=', product_uom.get("id"))],context={"active_test":False})
        uom = self._fill_product_uom(cr, uid, product_uom)

        if object_ids:
            return self.pool.get('product.uom').write(cr, uid, object_ids[0:1], uom, context)

        _logger.info("\ninserted : uom :\n")
        _logger.info(object_ids)
        _logger.info(uom)
        return self.pool.get('product.uom').create(cr, uid, uom, context)

    def create_or_update_product_uom_category(self,cr, uid, vals, context=None):
        product_uom_categ = json.loads(vals.get("product_uom_category"))
        uom_categ ={}
        uom_categ["name"] = product_uom_categ.get("name")
        uom_categ["uuid"] = product_uom_categ.get("id")
        object_ids = self.pool.get("product.uom.categ").search(cr, uid, [('uuid', '=', uom_categ["uuid"])])


        if object_ids :
            _logger.info("\nupdated : uom_categ:\n")
            _logger.info(uom_categ)
            return self.pool.get('product.uom.categ').write(cr, uid, object_ids[0:1], uom_categ, context)

        _logger.info("\ninserted : uom_categ:\n")
        _logger.info(uom_categ)
        return self.pool.get('product.uom.categ').create(cr, uid, uom_categ, context)


    def _fill_product_uom(self, cr, uid, product_uom_from_feed):
        product_uom ={}
        category = product_uom_from_feed.get("category")
        category_from_db = self.pool.get("product.uom.categ").search(cr, uid, [('uuid', '=', category["id"])])

        product_uom["name"] = product_uom_from_feed.get("name")
        product_uom["uuid"] = product_uom_from_feed.get("id")
        product_uom["active"] = product_uom_from_feed.get("isActive")
        ratio = float(product_uom_from_feed.get("ratio"))
        product_uom["factor"] = 1/ratio
        product_uom["category_id"] = category_from_db[0] if category_from_db else category_from_db

        uom_type = "reference"
        if ratio > 1:
            uom_type = "bigger"
        elif ratio < 1:
            uom_type = "smaller"

        product_uom["uom_type"] = uom_type
        return product_uom

