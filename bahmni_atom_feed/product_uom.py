import json
import logging

from dateutil.relativedelta import relativedelta
from osv import fields, osv
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class product_uom(osv.osv):

    _name = 'product.uom'
    _inherit = 'product.uom'

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom()

class product_uom_categ(osv.osv):

    _name = 'product.uom.categ'
    _inherit = 'product.uom.categ'

    _columns = {
        'uuid': fields.char('UUID', size=64)
    }
product_uom_categ()


class product_uom_service(osv.osv):
    _name = 'product.uom.service'
    _auto = False

    def create_or_update_product_uom(self,cr, uid, vals, context=None):
        product_uom = json.loads(vals.get("product_uom"))
        object_ids = self.pool.get("product.uom").search(cr, uid, [('uuid', '=', product_uom.get("id"))])
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
        product_uom["factor"] = ratio
        product_uom["category_id"] = category_from_db[0] if category_from_db else category_from_db

        uom_type = "reference"
        if ratio > 1:
            uom_type = "bigger"
        elif ratio < 1:
            uom_type = "smaller"

        product_uom["uom_type"] = uom_type
        return product_uom

    # def _get_object_by_uuid(self, cr, uid, object_type, uuid):
    #     object_ids = self.pool.get(object_type).search(cr, uid, [('uuid', '=', uuid)])
    #     return self._get_first_obj_for_object_ids(cr, uid, object_ids, object_type)
    #
    #
    # def _get_object_by_name_or_uuid(self, cr, uid, object_type, name, uuid):
    #     if uuid is not None:
    #         object_by_uuid = self._get_object_by_uuid(cr, uid, object_type, uuid)
    #         if object_by_uuid is not None: return object_by_uuid
    #
    #     object_ids = self.pool.get(object_type).search(cr, uid, [('name', '=', name)])
    #     return self._get_first_obj_for_object_ids(cr, uid, object_ids, object_type)


    # def _get_first_obj_for_object_ids(self, cr, uid, object_ids, object_type):
    #     if object_ids is not None and len(object_ids) > 0:
    #         obj = self.pool.get(object_type).read(cr, uid, object_ids[0])
    #       #  scalar_obj = obj[0] if obj and len(obj) > 0 else obj
    #         if obj is not None:
    #             return {"id": object_ids[0], "value": obj}
    #     return None

    # def _get_first_obj_for_object_ids(self, cr, uid, object_ids, object_type):
    #     if object_ids is not None and len(object_ids) > 0:
    #         obj = self.pool.get(object_type).read(cr, uid, object_ids[0])
    #         if obj is not None and len(obj)!= 0:
    #             return obj
    #     return None