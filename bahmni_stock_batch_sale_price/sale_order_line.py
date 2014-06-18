import logging
from osv import fields, osv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp import pooler
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare

import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

class sale_order_line(osv.osv):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    def _price(self, unit_price , batch_price):
        if(batch_price > 0):
            return batch_price
        else:
            return unit_price

    def _get_prodlot_context(self, cr, uid, context=None):
        context = context or {}
        shop_id = context.get('shop', False)
        shop_obj = self.pool.get('sale.shop')
        shop = shop_obj.browse(cr, uid, shop_id)
        prodlot_context = {}
        if(not shop_id):
            return {}
        if shop:
            location_id = shop.warehouse_id and shop.warehouse_id.lot_stock_id.id
            if location_id:
                prodlot_context['location_id'] = location_id
        return prodlot_context

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                          lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}

        lang = lang or context.get('lang',False)
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')

        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                              'product_uos_qty': qty}, 'domain': {'product_uom': [],
                                                                  'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)
        #-----------------populating batch id for sale order line item-----------------------------------------------------------
        stock_prod_lot = self.pool.get('stock.production.lot')
        sale_price = 0.0
        result['batch_name'] = None
        result['batch_id'] = None

        for prodlot_id in stock_prod_lot.search(cr, uid,[('product_id','=',product_obj.id)]):
            prodlot_context = self._get_prodlot_context(cr, uid, context=context)
            prodlot = stock_prod_lot.browse(cr, uid, prodlot_id, context=prodlot_context)
            if(prodlot.life_date and datetime.strptime(prodlot.life_date, tools.DEFAULT_SERVER_DATETIME_FORMAT) < datetime.today()):
                continue
            if qty <= prodlot.future_stock_forecast:
                sale_price = prodlot.sale_price
                result['batch_name'] = prodlot.name
                result['batch_id'] = prodlot.id
                break
        #-----------------------------------------------------------------

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                          [('category_id', '=', product_obj.uom_id.category_id.id)],
                      'product_uos':
                          [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
            # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                         'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                product, qty or 1.0, partner_id, {
                    'uom': uom or result.get('product_uom'),
                    'date': date_order,
                    })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                             "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': self._price(price,sale_price)})
        if warning_msgs:
            warning = {
                'title': _('Configuration Error!'),
                'message' : warning_msgs
            }

        res = {'value': result, 'domain': domain, 'warning': warning}
        # Code extracted From sale_stock.py
        if not product:
            res['value'].update({'product_packaging': False})
            return res

        #update of result obtained in super function
        res_packing = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
        res['value'].update(res_packing.get('value', {}))
        warning_msgs = res_packing.get('warning') and res_packing['warning']['message'] or ''
        res['value']['delay'] = (product_obj.sale_delay or 0.0)
        res['value']['type'] = product_obj.procure_method

        return res

    def onchange_product_dosage(self, cr, uid, ids, product_dosage, product_number_of_days, context=None):
        qty = product_dosage*product_number_of_days
        for sale_order_line in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, sale_order_line.id, {'product_uom_qty': qty})
        return {'value': {'product_uom_qty': qty}}

    _columns = {
        'batch_id': fields.many2one('stock.production.lot', 'Batch No'),
        'batch_name': fields.char('Batch No'),
        'product_dosage': fields.float('Dosage', digits_compute=dp.get_precision('Account')),
        'product_number_of_days': fields.integer('No. Days'),
    }

    _defaults = {
        'product_dosage': 1,
        'product_number_of_days': 1,
    }

sale_order_line()
