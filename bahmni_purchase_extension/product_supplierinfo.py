from openerp.osv import fields, osv
from openerp.osv.orm import browse_null
from openerp import pooler
import openerp.addons.decimal_precision as dp
import openerp
import logging
import re

_logger = logging.getLogger(__name__)

class product_supplierinfo(osv.osv):
    _name = "product.supplierinfo"
    _inherit = "product.supplierinfo"

    def _get_unit_price(self, cr, uid, ids, name, args, context=None):
        res = {}
        for product_supplierinfo in self.browse(cr, uid, ids):
            pricelist_ids =  self.pool.get('pricelist.partnerinfo').search(cr, uid, [('suppinfo_id','=',product_supplierinfo.id)]) or False
            pricelist = pricelist_ids and self.pool.get('pricelist.partnerinfo').browse(cr, uid, pricelist_ids[0], context) or False
            res[product_supplierinfo.id] = pricelist and pricelist.unit_price or 0
        return res

    _columns = {
        'manufacturer':fields.char('Manufacturer', size=128, help="Manufacturer of the product supplied."),
        'unit_price': fields.function(_get_unit_price, type='float', string='Unit Price')
    }


class pricelist_partnerinfo(osv.osv):
    _name = "pricelist.partnerinfo"
    _inherit = "pricelist.partnerinfo"

    _columns = {
        'price': fields.float('MRP', digits_compute= dp.get_precision('MRP')),
        'unit_price': fields.float('Unit Price', digits_compute= dp.get_precision('Product Unit Price')),
    }