import json
import logging

from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class drug_service(osv.osv):
    _name = 'drug.service'
    _auto = False

    def create_or_update_drug(self, cr, uid, vals, context=None):
        object_ids = self.pool.get("product.product").search(cr, uid, [('uuid', '=', vals.get("uuid"))], context={"active_test":False})
        updated_drug = self._fill_drug_object(cr, uid, vals, object_ids)
        if object_ids :
            prod_id = self.pool.get('product.product').write(cr, uid, object_ids[0:1], updated_drug, context)
        else:
            prod_id = self.pool.get('product.product').create(cr, uid, updated_drug, context)

    def _fill_drug_object(self, cr, uid, drug_from_feed, drug_ids_from_db):
        drug = {}
        category_name = drug_from_feed.get("dosageForm")
        category_from_db = self._get_object_by_domain(cr, uid, "product.category", [('name', '=', category_name)])
        categ_id = category_from_db and category_from_db.get('id') or self._create_in_drug_category(cr, uid, category_name)
        list_price = drug_ids_from_db and self.pool.get('product.product').browse(cr, uid, drug_ids_from_db[0]).list_price or 0.0

        drug["uuid"] = drug_from_feed.get("uuid")
        drug["name"] = drug_from_feed.get("name")
        drug["default_code"] = drug_from_feed.get("shortName")
        drug["drug"] = drug_from_feed.get("genericName")
        drug["categ_id"] = categ_id
        drug["type"] = "product"
        drug["list_price"] = list_price
        drug["sale_ok"] = 1
        drug["purchase_ok"] = 1
        return drug

    def _create_in_drug_category(self, cr, uid, name, context=None):
        parent_categ = self.pool.get("product.category").search(cr, uid, [('name', '=', "Drug")])
        category = {'name': name}
        if(parent_categ):
            category['parent_id'] = parent_categ[0]
        return self.pool.get('product.category').create(cr, uid, category)

    def create_or_update_drug_category(self, cr, uid, vals, context=None):
        drug_categ = json.loads(vals.get("drug_category"))
        exist_categ = self.pool.get("product.category").search(cr, uid, [('uuid', '=', drug_categ.get("id"))])
        parent_categ = self.pool.get("product.category").search(cr, uid, [('name', '=', "Drug")])
        updated_categ = self._fill_drug_category(cr,uid,drug_categ,parent_categ[0])

        if exist_categ:
            _logger.info("\nupdated : drug_category :\n")
            _logger.info(updated_categ)
            _logger.info(exist_categ[0:1])
            return self.pool.get('product.category').write(cr, uid, exist_categ[0:1], updated_categ)

        _logger.info("\ninserted : drug_category :\n")
        _logger.info(updated_categ)
        return self.pool.get('product.category').create(cr, uid, updated_categ)

    def _fill_drug_category(self,cr,uid,drug_categ_from_feed,parent_id=None):
        drug_categ = {}
        drug_categ["name"] = drug_categ_from_feed.get("name")
        drug_categ["uuid"] = drug_categ_from_feed.get("id")
        if parent_id is not None:
            drug_categ["parent_id"] = parent_id

        _logger.info("drug categ in fill")
        _logger.info(drug_categ)
        return drug_categ


    def _get_object_by_uuid(self, cr, uid, object_type, uuid):
        object_ids = self.pool.get(object_type).search(cr, uid, [('uuid', '=', uuid)])
        obj = self.pool.get(object_type).read(cr, uid, object_ids)
        if obj:
            return obj[0]
        return None

    def _get_object_by_domain(self, cr, uid, object_type, domain=None):
        object_ids = self.pool.get(object_type).search(cr, uid, domain)
        obj = self.pool.get(object_type).read(cr, uid, object_ids)
        if obj:
            return obj[0]
        return None
