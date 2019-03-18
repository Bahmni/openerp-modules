import logging

from openerp.osv import osv

_logger = logging.getLogger(__name__)


class reference_data_service(osv.osv):
    _name = "reference.data.service"
    _auto = False

    def create_or_update_reference_data(self, cr, uid, vals, context=None):
        object_ids = self.pool.get("product.product").search(
            cr,
            uid,
            [('uuid', '=', vals.get("uuid"))],
            context={"active_test": False})

        updated_reference_data = self._fill_reference_data_object(
            cr, uid, vals)
        if object_ids:
            prod_id = self.pool.get('product.product').write(
                cr, uid, object_ids[0:1], updated_reference_data, context)
        else:
            prod_id = self.pool.get('product.product').create(
                cr, uid, updated_reference_data, context)
        return prod_id

    def _fill_reference_data_object(self, cr, uid, reference_data_from_feed):
        reference_data = {}
        category_name = self._get_category(reference_data_from_feed.get("product_category"))
        category_hierarchy = self._get_category_hierarchy()

        category_from_db = self._get_object_by_domain(
            cr, uid, "product.category", [('name', '=', category_name)])

        categ_id = category_from_db and category_from_db.get(
            'id') or self._create_reference_data_category(
                cr, uid, category_name, category_hierarchy)

        reference_data["uuid"] = reference_data_from_feed.get("uuid")
        reference_data["name"] = reference_data_from_feed.get("name")
        reference_data["active"] = reference_data_from_feed.get("is_active")
        reference_data["categ_id"] = categ_id
        reference_data["sale_ok"] = 1
        reference_data["purchase_ok"] = 0
        reference_data["type"] = "service"
        return reference_data

    def _get_category(self, ref_category=None):
        raise NotImplementedError

    def _get_category_hierarchy(self):
        raise NotImplementedError

    def _create_reference_data_category(self, cr, uid, name,
                                        category_hierarchy, context=None):
        category_id = self._create_category_in_hierarchy(
            cr, uid, context, name, category_hierarchy)
        return category_id

    def _get_object_by_uuid(self, cr, uid, object_type, uuid):
        object_ids = self.pool.get(object_type).search(cr, uid, [('uuid', '=',
                                                                  uuid)])
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
