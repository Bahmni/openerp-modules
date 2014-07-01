from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
from openerp import netsvc
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import logging
_logger = logging.getLogger(__name__)


class stock_move(osv.osv):
    _name = "stock.move"
    _inherit = "stock.move"

    def onchange_lot_id(self, cr, uid, ids, prodlot_id=False, product_qty=False,
                        loc_id=False, product_id=False, uom_id=False, context=None):
        """ On change of production lot gives a warning message.
        @param prodlot_id: Changed production lot id
        @param product_qty: Quantity of product
        @param loc_id: Location id
        @param product_id: Product id
        @return: Warning message
        """
        if not prodlot_id or not loc_id:
            return {}
        ctx = context and context.copy() or {}
        ctx['location_id'] = loc_id
        ctx.update({'raise-exception': True})
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        product_uom = product_obj.browse(cr, uid, product_id, context=ctx).uom_id
        prodlot = self.pool.get('stock.production.lot').browse(cr, uid, prodlot_id, context=ctx)
        location = self.pool.get('stock.location').browse(cr, uid, loc_id, context=ctx)
        uom = uom_obj.browse(cr, uid, uom_id, context=ctx)
        amount_actual = uom_obj._compute_qty_obj(cr, uid, product_uom, prodlot.stock_available, uom, context=ctx)

        warning = {}
        if (location.usage == 'internal') and (product_qty > (amount_actual or 0.0)):
            warning = {
                'title': _('Insufficient Stock for Serial Number !'),
                'message': _('You are moving %.2f %s but only %.2f %s available for this serial number.') % (product_qty, uom.name, amount_actual, uom.name)
            }

        if(prodlot.life_date and datetime.strptime(prodlot.life_date, DEFAULT_SERVER_DATETIME_FORMAT) < datetime.today()):
            warning = {
                'title': _('Batch is expired'),
                'message': _('This product is expired on %s') % (prodlot.life_date)
            }

        return {'warning': warning}

    def _get_stock_for_location(self, cr, uid, loc_id, prod_id):
        qty = 0
        cr.execute('''select
                    prodlot_id,
                    qty
                from
                    batch_stock_future_forecast
                where
                    location_id = %s and product_id = %s ''',(loc_id, prod_id,))
        sum_qty = 0.0
        prodlot_qty_map = {}
        for row in cr.dictfetchall():
            if((row['prodlot_id'] != None) ):
                prodlot_qty_map[row['prodlot_id']] = row['qty']
            else :
                if(row['qty'] > 0):
                    sum_qty += row['qty']
        for lot_id, qty in prodlot_qty_map.iteritems():
            if(qty >=0 ):
                prod_lot = self.pool.get('stock.production.lot').browse(cr, uid, lot_id)
                if(prod_lot and prod_lot.life_date):
                    if(datetime.today() <= datetime.strptime(prod_lot.life_date, DEFAULT_SERVER_DATETIME_FORMAT)):
                        sum_qty += qty

        return sum_qty

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False, context=None):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {}
        lang = False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id  = product.uos_id and product.uos_id.id or False
        qty =0.0
        if(loc_id):
            qty = self._get_stock_for_location(cr, uid, loc_id, prod_id)

        result = {
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_qty': 0.00,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
            'prodlot_id' : False,
            'stock_available':qty
            }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}


    def onchange_quantity(self, cr, uid, ids, product_id, product_qty,
                          product_uom, product_uos,loc_id=False,move_lines=None, context=None):
        """ On change of product quantity finds UoM and UoS quantities
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @param product_uos: Unit of sale of product
        @return: Dictionary of values
        """
        result = {
            'product_uos_qty': 0.00
        }
        warning = {}

        if (not product_id) or (product_qty < 0.0):
            result['product_qty'] = 0.0
            return {'value': result}

        product_obj = self.pool.get('product.product')
        uos_coeff = product_obj.read(cr, uid, product_id, ['uos_coeff'])

        # Warn if the quantity was decreased
        if ids:
            for move in self.read(cr, uid, ids, ['product_qty']):
                if product_qty < move['product_qty']:
                    warning.update({
                        'title': _('Information'),
                        'message': _("By changing this quantity here, you accept the "
                                     "new quantity as complete: OpenERP will not "
                                     "automatically generate a back order.") })
                break

        prod_uom_obj = None
        factor = 1
        if product_uos and product_uom and (product_uom != product_uos):
            result['product_uos_qty'] = product_qty * uos_coeff['uos_coeff']
        else:
            result['product_uos_qty'] = product_qty

        if(product_uom):
            prod_uom_obj = self.pool.get('product.uom').browse(cr,uid,product_uom)
            factor = prod_uom_obj.factor

        qty = 0.0
        if(loc_id):
            qty = self._get_stock_for_location(cr, uid, loc_id, product_id) * factor - product_qty

        if(move_lines):
            for move in move_lines:
                move_line = move[2]
                if(move_line and move_line['product_id'] and move_line['product_id'] == product_id):
                    qty -= move_line['product_qty']
            for move in move_lines:
                move_line = move[2]
                if(move_line and move_line['product_id'] and move_line['product_id'] == product_id):
                    move_line['product_qty'] = qty

        result['stock_available'] = qty
        result['move_lines'] = move_lines

        return {'value': result, 'warning': warning,'stock_available':qty}

    def _get_picking_time(self, cr, uid, ids, name, args, context=None):
        res = {}
        for stock_move in self.browse(cr, uid, ids):
            res[stock_move.id] = stock_move.picking_id.date
        return res

    _columns={
        'stock_available': fields.float("Balance",digits_compute=dp.get_precision('Account'),),
        'stock_picking_time': fields.function(_get_picking_time, type='datetime', string='Move Date', store=True),
    }

class split_in_production_lot(osv.osv_memory):
    _name = "stock.move.split"
    _inherit = "stock.move.split"

    _columns = {
        'stock_move': fields.many2one('stock.move', 'Stock Move', required=False)
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(split_in_production_lot, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id'):
            move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
            if 'product_id' in fields:
                res.update({'product_id': move.product_id.id})
            if 'product_uom' in fields:
                res.update({'product_uom': move.product_uom.id})
            if 'qty' in fields:
                res.update({'qty': move.product_qty})
            if 'use_exist' in fields:
                res.update({'use_exist': (move.picking_id and (move.picking_id.type=='out' or move.picking_id.type=='internal') and True) or False})
            if 'location_id' in fields:
                res.update({'location_id': move.location_id.id})
            if 'stock_move' in fields:
                res.update({'stock_move': move.id})
        return res
