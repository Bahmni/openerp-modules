import json
import uuid
from psycopg2._psycopg import DATETIME
from openerp import netsvc
from openerp.osv import fields, osv
import logging
import datetime

_logger = logging.getLogger(__name__)


class lab_test_service(osv.osv):
    _name = 'lab.test.service'
    _auto = False

    def create_or_update_labtest(self, cr, uid, vals, context=None):
        lab_test = json.loads(vals.get("lab_test"))
        name = lab_test.get("name")
        short_name = lab_test.get("shortName")
        uuid = lab_test.get("id")
        sale_price = lab_test.get("salePrice")
        category_name = lab_test.get("category")
        categ_id = -1

        category_hierarchy = ["Lab", "Services", "All Products"]

        category_ids = self.pool.get('product.category').search(cr, uid, [('name', '=', category_name)])
        if (len(category_ids) > 0):
            categ_id = category_ids[0]
        else:
            categ_id = self.create_category_in_hierarchy(cr, uid, context, category_name, category_hierarchy)

        acc_journal_id = self.pool.get('account.journal').search(cr, uid, [('name', '=', 'Cash')])[0]

        if(categ_id != -1):
            data = {
                'uuid': uuid,
                'name': name,
                'list_price': sale_price,
                'standard_price': sale_price,
                'default_code': short_name,
                'category': category_name,
                'categ_id': categ_id
            }

            _logger.info("saving product : ")
            _logger.info(data)
            prod_id = self.pool.get('product.product').create(cr, uid, data, context)
            _logger.info("Done saving!!")


    def create_category_in_hierarchy(self, cr, uid, context, category_name, category_hierarchy):

        category_ids = self.pool.get('product.category').search(cr, uid, [('name', '=', category_hierarchy[0])])
        if (len(category_ids) > 0):
            parent_id = category_ids[0]
        else:
            if (len(category_hierarchy) > 0):
                parent_id = self.create_category(cr, uid, category_hierarchy[0], category_hierarchy[1:])       #create the hierarchy
            else:
                parent_id = self.create_category(cr, uid, category_hierarchy[0], 0)                            #create root node of the hierarchy

        if (parent_id != -1):
            data = {
                'name': category_name,
                'parent_id': parent_id
            }

            return self.pool.get('product.category').create(cr, uid, data, context)





