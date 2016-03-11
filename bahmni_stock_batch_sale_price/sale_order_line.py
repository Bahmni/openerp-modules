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
from openerp.tools import pickle
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
                prodlot_context['search_in_child'] = True
        return prodlot_context

    def get_available_batch_details(self, cr, uid, product_id, sale_order, context=None):
        context = context or {}
        context['shop'] = sale_order.shop_id.id
        prodlot_context = self._get_prodlot_context(cr, uid, context=context)
        stock_prod_lot = self.pool.get('stock.production.lot')

        already_used_batch_ids = []
        for line in sale_order.order_line:
            if line.batch_id:
                id = line.batch_id.id
                already_used_batch_ids.append(id.__str__())

        query = ['&',('product_id','=',product_id), ('id','not in',already_used_batch_ids)] if len(already_used_batch_ids) > 0 else [('product_id','=',product_id)]
        for prodlot_id in stock_prod_lot.search(cr, uid, query, context=prodlot_context):
            prodlot = stock_prod_lot.browse(cr, uid, prodlot_id, context=prodlot_context)
            if(prodlot.life_date and datetime.strptime(prodlot.life_date, tools.DEFAULT_SERVER_DATETIME_FORMAT) >= datetime.today() and prodlot.future_stock_forecast > 0):
                return prodlot
        return None

    def batch_id_change(self, cr, uid, ids, batch_id, product_id, context=None):
        if not product_id:
            return {}
        if not batch_id:
            prod_obj = self.pool.get('product.product').browse(cr, uid, product_id)
            return {'value': {'price_unit': prod_obj.list_price}}
        context = context or {}
        stock_prod_lot = self.pool.get('stock.production.lot')
        sale_price = 0.0
        for prodlot in stock_prod_lot.browse(cr, uid, [batch_id], context=context):
            sale_price =  prodlot.sale_price
        return {'value' : {'price_unit': sale_price}}


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
                              'batch_id': None,
                              'price_unit': 0.0,
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
        result['expiry_date'] = None

        prodlot_context = self._get_prodlot_context(cr, uid, context=context)
        for prodlot_id in stock_prod_lot.search(cr, uid,[('product_id','=',product_obj.id)],context=prodlot_context):
            prodlot = stock_prod_lot.browse(cr, uid, prodlot_id, context=prodlot_context)
            life_date = prodlot.life_date and datetime.strptime(prodlot.life_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            if life_date and life_date < datetime.today():
                continue
            if qty <= prodlot.future_stock_forecast:
                sale_price = prodlot.sale_price
                result['batch_name'] = prodlot.name
                result['batch_id'] = prodlot.id
                result['expiry_date'] = life_date.strftime('%d/%m/%Y') if (type(life_date) == 'datetime.datetime') else None
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
            tax_id = product_obj.taxes_id
            if not tax_id:
                search_criteria = [
                    ('key', '=', 'default'),
                    ('model', '=', 'product.product'),
                    ('name', '=', 'taxes_id'),
                ]
                ir_values_obj = self.pool.get('ir.values')
                defaults = ir_values_obj.browse(cr, uid, ir_values_obj.search(cr, uid, search_criteria))
                default_tax_id = pickle.loads(defaults[0].value.encode('utf-8')) if defaults else None
                if default_tax_id:
                    tax_id = self.pool.get('account.tax').browse(cr, uid, default_tax_id)

            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, tax_id)

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

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        res["batch_name"] = line.batch_name
        res["expiry_date"] = line.expiry_date
        return res

    def _in_stock(self, cr, uid, sale_order_line_ids, field_name, arg, context=None ):
        returnData = {}
        prod_total_qty_map={}
        for sale_order_line_id in sale_order_line_ids:
            sale_order_line_obj = self.pool.get('sale.order.line').browse(cr, uid, sale_order_line_id)
            product_id = sale_order_line_obj.product_id.id
            qty = sale_order_line_obj.product_uom_qty
            if product_id in prod_total_qty_map:
                prod_total_qty_map[product_id] = (prod_total_qty_map[product_id] + qty)
            else:
                prod_total_qty_map[product_id] = qty
        for sale_order_line_id in sale_order_line_ids:
            sale_order_line_obj = self.pool.get('sale.order.line').browse(cr, uid, sale_order_line_id)
            product_id = sale_order_line_obj.product_id.id
            location_id = sale_order_line_obj.order_id.shop_id.warehouse_id.lot_stock_id.id

            stock_qty = self.pool.get('product.product').get_stock_for_location(cr, uid, location_id, product_id)
            returnData[sale_order_line_id] = stock_qty >= prod_total_qty_map[product_id]

        return returnData

    _columns = {
        'batch_id': fields.many2one('stock.production.lot', 'Batch No'),
        'batch_name': fields.char('Batch No'),
        'expiry_date': fields.char('Expiry Date'),
        'comments': fields.char('Comments'),
        'flag_in_stock': fields.function(_in_stock, string="In Stock", type='boolean')
    }

    _defaults = {
        'flag_in_stock': True
    }

    _order = 'id'

sale_order_line()
