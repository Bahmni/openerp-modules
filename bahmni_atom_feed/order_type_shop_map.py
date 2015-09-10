from openerp.osv import fields, osv

class order_type_shop_map(osv.osv):
    _name = "order.type.shop.map"
    _description = "Order Type to Shop Mapping"
    _columns = {
        'order_type': fields.char('Order Type', required=True, size=64),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
        'location_name' : fields.char('Location Name')
    }

order_type_shop_map()
