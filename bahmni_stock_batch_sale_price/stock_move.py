# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class split_in_production_lot_with_price(osv.osv_memory):
    _name = "stock.move.split"
    _inherit = "stock.move.split"
    _description = "Split in Serial Numbers"

    def split_lot(self, cr, uid, ids, context=None):
        """ To split a lot"""
        if context is None:
            context = {}
        res = self.split(cr, uid, ids, context.get('active_ids'), context=context)
        return {'type': 'ir.actions.act_window_close'}

    def split(self, cr, uid, ids, move_ids, context=None):
        """ To split stock moves into serial numbers

        :param move_ids: the ID or list of IDs of stock move we want to split
        """
        if context is None:
            context = {}
        assert context.get('active_model') == 'stock.move',\
             'Incorrect use of the stock move split wizard'
        inventory_id = context.get('inventory_id', False)
        prodlot_obj = self.pool.get('stock.production.lot')
        inventory_obj = self.pool.get('stock.inventory')
        move_obj = self.pool.get('stock.move')
        new_move = []
        for data in self.browse(cr, uid, ids, context=context):
            for move in move_obj.browse(cr, uid, move_ids, context=context):
                move_qty = move.product_qty
                quantity_rest = move.product_qty
                uos_qty_rest = move.product_uos_qty
                new_move = []
                if data.use_exist:
                    lines = [l for l in data.line_exist_ids if l]
                else:
                    lines = [l for l in data.line_ids if l]
                total_move_qty = 0.0
                for line in lines:
                    quantity = line.quantity
                    total_move_qty += quantity
                    if total_move_qty > move_qty:
                        raise osv.except_osv(_('Processing Error!'), _('Serial number quantity %d of %s is larger than available quantity (%d)!') \
                                % (total_move_qty, move.product_id.name, move_qty))
                    if quantity <= 0 or move_qty == 0:
                        continue
                    quantity_rest -= quantity
                    uos_qty = quantity / move_qty * move.product_uos_qty
                    uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty

                    if quantity_rest < 0:
                        quantity_rest = quantity
                        self.pool.get('stock.move').log(cr, uid, move.id, _('Unable to assign all lots to this move!'))
                        return False
                    default_val = {
                        'product_qty': quantity,
                        'product_uos_qty': uos_qty,
                        'state': move.state
                    }
                    if quantity_rest > 0:
                        current_move = move_obj.copy(cr, uid, move.id, default_val, context=context)
                        if inventory_id and current_move:
                            inventory_obj.write(cr, uid, inventory_id, {'move_ids': [(4, current_move)]}, context=context)
                        new_move.append(current_move)

                    if quantity_rest == 0:
                        current_move = move.id
                    prodlot_id = False
                    if data.use_exist:
                        prodlot_id = line.prodlot_id.id
                    if not prodlot_id:
                        prodlot_id = prodlot_obj.create(cr, uid, {
                            'name': line.name,
                            'sale_price':line.sale_price * move.product_uom.factor,
                            'cost_price':line.cost_price * move.product_uom.factor,
                            'mrp':line.mrp * move.product_uom.factor,
                            'life_date':line.expiry_date,
                            'product_id': move.product_id.id},
                        context=context)

                    move_obj.write(cr, uid, [current_move], {'prodlot_id': prodlot_id, 'state':move.state})

                    update_val = {}
                    if quantity_rest > 0:
                        update_val['product_qty'] = quantity_rest
                        update_val['product_uos_qty'] = uos_qty_rest
                        update_val['state'] = move.state
                        move_obj.write(cr, uid, [move.id], update_val)

        return new_move

split_in_production_lot_with_price()

class stock_move_split_lines_exist_with_price(osv.osv_memory):
    _name = "stock.move.split.lines"
    _description = "Stock move Split lines"
    _inherit = "stock.move.split.lines"

    def _get_product_uom(self, cr, uid, context=None):
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_uom_id = context.get('product_uom', None)
        if(product_uom_id is not None):
            return product_uom_obj.browse(cr, uid, product_uom_id, context=context)


    def _get_product_uom_name(self, cr, uid, context=None):
        product_uom = self._get_product_uom(cr, uid, context=context)
        if(product_uom is not None):
            return product_uom.name

    def _get_default_cost_price(self, cr, uid, context=None):
        context = context or {}
        stock_move_id = context.get('stock_move', None)
        stock_move = stock_move_id and self.pool.get('stock.move').browse(cr, uid, stock_move_id, context=context)
        return (stock_move and stock_move.price_unit) or 0.0

    _columns = {
        'cost_price': fields.float('Cost Price', digits_compute=dp.get_precision('Product Price')),
        'sale_price': fields.float('Sale Price', digits_compute=dp.get_precision('Product Price')),
        'mrp': fields.float('MRP', digits_compute=dp.get_precision('Product Price')),
        'expiry_date': fields.date('Life Date'),
        'product_uom': fields.char("Unit", store=False),
    }

    _defaults = {
        'product_uom': _get_product_uom_name,
        'cost_price': _get_default_cost_price,
    }

stock_move_split_lines_exist_with_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
