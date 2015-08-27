# -*- coding: utf-8 -*-
import logging
import simplejson
import time
import os
import re
import openerp
import pytz
from dateutil import parser
from datetime import datetime
from dateutil.tz import tzlocal

from openerp.modules.registry import RegistryManager
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template
from openerp import pooler, tools
from bahmni_print_bill.number_to_marathi import convert

import openerp.addons.web.http as openerpweb


import logging

_logger = logging.getLogger(__name__)
_localtimezone = tzlocal()

class InvoiceController(openerp.addons.web.http.Controller):
    _cp_path = '/invoice'

    @openerpweb.jsonrequest
    def bill(self, req, voucher_id):
        uid = req.session._uid
        dbname = req.session._db
        context = req.session.context
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            pool = pooler.get_pool(dbname)
            account_voucher_obj = registry.get('account.voucher')
            company_obj = registry.get('res.company')
            sale_order_obj = pool.get('sale.order')
            invoice_obs = pool.get("account.invoice")
            voucher = account_voucher_obj.browse(cr, uid, voucher_id, context=context)
            company = company_obj.browse(cr, uid, voucher.company_id.id, context=context)
            voucher_line_ids = sorted(voucher.line_ids, key=lambda v: v.id,reverse=True)
            invoice = None
            for voucher_line in voucher_line_ids:
                if(voucher_line.type == 'cr'):
                    inv_no = voucher_line.name
                    inv_ids = invoice_obs.search(cr, uid,[('number','=',inv_no)])
                    if(inv_ids and len(inv_ids) > 0):
                        inv_id = inv_ids[0]
                        invoice = invoice_obs.browse(cr,uid,inv_id,context=context)
                    break
            invoice_line_items = []

            for invoice_line_item in invoice.invoice_line:
                invoice_line_items.append({
                    'product_name': invoice_line_item.product_id.name,
                    'unit_price': invoice_line_item.price_unit,
                    'quantity': invoice_line_item.quantity,
                    'subtotal': invoice_line_item.price_subtotal,
                    'product_category': invoice_line_item.product_id.categ_id.name,
                    'expiry_date': invoice_line_item.expiry_date if invoice_line_item.expiry_date else None,
                })
            number, number_in_words = convert(voucher.bill_amount)

            invoice_perm = invoice_obs.perm_read(cr, uid, [invoice.id])[0]
            bill_confirmed_date = invoice_perm.get('write_date', 'N/A')
            bill_create_date = invoice_perm.get('create_date', 'N/A')
            sale_order_ids = sale_order_obj.search(cr, uid, [('name', '=', invoice.reference)], context=context)
            if sale_order_ids:
                sale_order_perm = sale_order_obj.perm_read(cr, uid, sale_order_ids, context=context)[0]
                bill_create_date = sale_order_perm.get('create_date', 'N/A')

            bill = {
                'company': {
                    'name': company.name,
                    'phone': company.phone,
                    'vat': company.vat,
                    'logo': str(company.logo_web),
                    'address': {
                        'street': str(company.street) + ", " + str(company.street2),
                        'city': company.city,
                        'zip': company.zip,
                    }
                },
                'voucher_number': voucher.number,
                'voucher_date': voucher.date,
                'invoice_line_items': invoice_line_items,
                'new_charges': voucher.bill_amount + invoice.discount,
                'discount_head': invoice.discount_acc_id and invoice.discount_acc_id.name or None,
                'discount': invoice.discount,
                'net_amount': voucher.bill_amount,
                'net_amount_string': number+"/-",
                'net_amount_words': number + "/- (" + number_in_words + " फक्त)",
                'previous_balance': voucher.balance_amount + voucher.amount - voucher.bill_amount,
                'bill_amount': voucher.amount + voucher.balance_amount,
                'paid_amount': voucher.amount,
                'balance_amount': voucher.balance_amount,
                'partner_name': voucher.partner_id.name,
                'partner_local_name': voucher.partner_id.local_name,
                'partner_ref': voucher.partner_id.ref,
                'partner_uuid': voucher.partner_id.uuid,
                'cashier_initials': voucher.create_uid.initials,
                'bill_confirmed_date': parser.parse(bill_confirmed_date).replace(tzinfo=pytz.utc).astimezone(_localtimezone).strftime("%d/%m/%Y %H:%M:%S"),
                'bill_create_date': parser.parse(bill_create_date).replace(tzinfo=pytz.utc).astimezone(_localtimezone).strftime("%d/%m/%Y %H:%M:%S")
            }
            return bill
        return {}
