# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import re
import openerp
from openerp.modules.registry import RegistryManager
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template
from openerp import pooler, tools
from bahmni_print_bill.number_to_marathi import convert
import openerp.addons.web.http as openerpweb

import logging

_logger = logging.getLogger(__name__)

class QuotationController(openerp.addons.web.http.Controller):
    _cp_path = '/quotations'

    @openerpweb.httprequest
    def latest(self, req, patient_ref,dispensed,location_ref):
        uid = req.session._uid or 1
        dbname = req.session._db or "openerp"
        context = req.session.context or {}
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            pool = pooler.get_pool(dbname);
            patient_id = pool.get('res.partner').search(cr, uid, [('ref', '=', patient_ref)])

            shop_id = None
            local_shop_id = None

            shop_mapping = pool.get('order.type.shop.map').search(cr, uid, [('location_name', '=', location_ref)])
            if shop_mapping :
                shop_id = pool.get('order.type.shop.map').browse(cr, uid, shop_mapping[0], context=context).shop_id
                local_shop_id = pool.get('order.type.shop.map').browse(cr, uid, shop_mapping[0], context=context).local_shop_id

            sale_order_id_nondispensed =[]

            if shop_id != None:
                sale_order_id_nondispensed = pool.get('sale.order').search(cr, uid, [('partner_id', 'in', patient_id), ('state', '=', 'draft'), ('origin', '=', "ATOMFEED SYNC"),('shop_id','=',shop_id.id)])
            else:
                sale_order_ids = pool.get('sale.order').search(cr, uid, [('partner_id', 'in', patient_id), ('state', '=', 'draft'), ('origin', '=', "ATOMFEED SYNC")])
                for sale_order_id in sale_order_ids:
                    sale_order_line_ids = pool.get('sale.order.line').search(cr, uid, [('order_id', '=', sale_order_id)], context=context)
                    sale_order_lines = pool.get('sale.order.line').browse(cr, uid, sale_order_line_ids[0], context=context)
                    if(sale_order_lines.dispensed_status == 'false'):
                        sale_order_id_nondispensed.append(sale_order_id)


            if local_shop_id != None:
                sale_order_id_dispensed = pool.get('sale.order').search(cr, uid, [('partner_id', 'in', patient_id), ('state', '=', 'draft'), ('origin', '=', "ATOMFEED SYNC"),('shop_id','=',local_shop_id.id)])
            else:
                sale_order_id_dispensed =[];





            if(dispensed == 'true') :
                if(len(sale_order_id_dispensed) > 0):
                    quotation_id = sale_order_id_dispensed[0]
                    redirect_link = "/#id={0}&view_type=form&model=sale.order&menu_id=296&action=372".format(quotation_id)
                else:
                    redirect_link = "/#view_type=list&model=sale.order&menu_id=296&action=372"

            elif dispensed == 'false':
                if(len(sale_order_id_nondispensed) > 0):
                    quotation_id = sale_order_id_nondispensed[0]
                    redirect_link = "/#id={0}&view_type=form&model=sale.order&menu_id=296&action=372".format(quotation_id)
                else:
                    redirect_link = "/#view_type=list&model=sale.order&menu_id=296&action=372"

            else:
                redirect_link = "/#view_type=list&model=sale.order&menu_id=296&action=372"


            return """
            <html>
                <head>
                    <script type='text/javascript'>
                        window.location='{0}'
                    </script>
                </head>
            </html>""".format(redirect_link)
