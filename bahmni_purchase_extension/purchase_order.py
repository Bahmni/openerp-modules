from openerp.osv import fields, osv
from openerp import pooler

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
