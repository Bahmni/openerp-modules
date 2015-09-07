import logging

from openerp.osv import osv

_logger = logging.getLogger(__name__)


class radiology_test_service(osv.osv):
    _name = "radiology.test.service"
    _auto = False

    def create_or_update_radiology_test(self, cr, uid, vals, context=None):
        object_ids = self.pool.get("product.product").search(
            cr,
            uid,
            [('uuid', '=', vals.get("uuid"))],
            context={"active_test": False})

        updated_radiology_test = self._fill_radiology_test_object(
            cr, uid, vals, object_ids)
        if object_ids:
            prod_id = self.pool.get('product.product').write(
                cr, uid, object_ids[0:1], updated_radiology_test, context)
        else:
            prod_id = self.pool.get('product.product').create(
                cr, uid, updated_radiology_test, context)
        return prod_id

    def _fill_radiology_test_object(self, cr, uid, radiology_test_from_feed,
                                    radiology_test_ids_from_db):
        radiology_test = {}
        category_name = "Radiology"
        category_from_db = self._get_object_by_domain(
            cr, uid, "product.category", [('name', '=', category_name)])
        categ_id = category_from_db and category_from_db.get(
            'id') or self._create_radiology_category(cr, uid, category_name)
        radiology_test["uuid"] = radiology_test_from_feed.get("uuid")
        radiology_test["name"] = radiology_test_from_feed.get("name")
        radiology_test["categ_id"] = categ_id
        radiology_test["sale_ok"] = 1
        radiology_test["purchase_ok"] = 0
        radiology_test["type"] = "service"
        radiology_test["list_price"] = 0
        return radiology_test

    def _create_radiology_category(self, cr, uid, name, context=None):
        category_hierarchy = ["Services", "All Products"]
        category_id = self._create_category_in_hierarchy(
            cr, uid, context, name, category_hierarchy)
        return category_id

    def _create_category_in_hierarchy(
            self, cr, uid, context, category_name, category_hierarchy):
        if (len(category_hierarchy) > 0):
            category_ids = self.pool.get('product.category').search(
                cr, uid, [('name', '=', category_hierarchy[0])])
            if (len(category_ids) > 0):
                parent_id = category_ids[0]
            else:
                parent_category_name = category_hierarchy[0]
                del category_hierarchy[0]
                parent_id = self._create_category_in_hierarchy(
                    cr, uid, context, parent_category_name, category_hierarchy)
            return self.pool.get('product.category').create(
                cr, uid, {'name': category_name,
                          'parent_id': parent_id}, context)
        else:
            return self.pool.get('product.category').create(
                cr, uid, {'name': category_name}, context)

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
