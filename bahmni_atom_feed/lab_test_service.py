import json
import logging

from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv


_logger = logging.getLogger(__name__)


class lab_test_service(osv.osv):
    _name = 'lab.test.service'
    _auto = False

    def create_or_update_labtest(self, cr, uid, vals, context=None):
        lab_test_from_feed = json.loads(vals.get("lab_test"))
        lab_test_ids = self.pool.get('product.product').search(cr, uid, [('uuid', '=', lab_test_from_feed.get("id"))],context={"active_test":False})
        category_name = lab_test_from_feed.get("category")
        category_ids = self.pool.get('product.category').search(cr, uid, [('name', '=', category_name)])
        category_hierarchy = ["Lab", "Services", "All Products"]
        sale_unit_of_measure  = self.pool.get("product.uom").search(cr, uid, [('name', '=', "Unit(s)")])

        if (len(category_ids) > 0):
            categ_id = category_ids[0]
        else:
            categ_id = self._create_category_in_hierarchy(cr, uid, context, category_name, category_hierarchy)

        lab_test = {
            'uuid': lab_test_from_feed.get("id"),
            'name': lab_test_from_feed.get("name"),
            'list_price': lab_test_from_feed.get("salePrice"),
            'default_code': lab_test_from_feed.get("shortName"),
            'categ_id': categ_id,
            'active' : lab_test_from_feed.get("isActive"),
            'uom_id' : sale_unit_of_measure[0] if sale_unit_of_measure else sale_unit_of_measure,
            'type' : "service",
            'sale_ok' : 1,
            'purchase_ok' : 0
        }

        _logger.info("saving product : ")
        _logger.info(lab_test)

        if lab_test_ids :
            return self.pool.get('product.product').write(cr, uid,lab_test_ids[0:1], lab_test, context)

        return self.pool.get('product.product').create(cr, uid, lab_test, context)

    def _create_category_in_hierarchy(self, cr, uid, context, category_name, category_hierarchy):

        if (len(category_hierarchy) > 0):
            category_ids = self.pool.get('product.category').search(cr, uid, [('name', '=', category_hierarchy[0])])
            if (len(category_ids) > 0):
                parent_id = category_ids[0]
            else:
                parent_category_name = category_hierarchy[0];
                del category_hierarchy[0]
                parent_id = self._create_category_in_hierarchy(cr, uid, context, parent_category_name, category_hierarchy)
            return self.pool.get('product.category').create(cr, uid, {'name': category_name, 'parent_id': parent_id}, context)
        else:
            return self.pool.get('product.category').create(cr, uid, {'name': category_name}, context)






