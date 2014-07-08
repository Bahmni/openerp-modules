from openerp.osv import fields, osv
from openerp import pooler
import openerp


class purchase_order(osv.osv):

    _name = "purchase.order"
    _inherit = "purchase.order"

    def _default_to_only(self, cr, uid, context=None):
        stock_warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = stock_warehouse_obj.search(cr, uid, [])
        return warehouse_ids[0] if (len(warehouse_ids) == 1) else False

    _defaults = {
        'warehouse_id': _default_to_only
    }

class purchase_order_line(osv.osv):

    _name = "purchase.order.line"
    _inherit = "purchase.order.line"

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, context=None):
        res = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, 
            qty, uom_id, partner_id, date_order, fiscal_position_id, date_planned, name, price_unit, context)
        if (product_id):
            product = self.pool.get('product.product').browse(cr, uid, product_id, context)
            res['value']['manufacturer'] = product and product.manufacturer or False
        return res

    _columns = {
        'manufacturer':fields.char('Manufacturer', size=64),
    }


class stock_partial_picking(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def is_field_empty(self, vals, field_name):
        for key in vals:
            for list_item in vals[key]:
                for item in list_item:
                    if isinstance(item, dict):
                        if not item[field_name]:
                            return False
        return True

    def create(self, cr, uid, vals, context=None):
        if not self.is_field_empty(vals, 'prodlot_id'):
            raise openerp.exceptions.Warning('Please enter a Serial Number.')
        return super(stock_partial_picking, self).create(cr, uid, vals, context=context)