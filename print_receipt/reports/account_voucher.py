# -*- coding: utf-8 -*-

import time
from openerp.report import report_sxw
from openerp import pooler
import re
import logging
_logger = logging.getLogger(__name__)


class account_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_voucher, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                                  'time': time,
                                  'getLines': self._lines_get,
                                  'getInvoiceLines': self._invoice_lines_get,
                                  'getInvoiceDiscount': self._invoice_discount_get,
                                  'getInvoiceDiscountHead': self._invoice_discount_head_get,
                                  'getInvoiceRoundOff': self._invoice_roundoff_get,
                                  'removeInternalRef': self._remove_internal_ref,
                                  })
        self.context = context

    def _lines_get(self, voucher):
        voucherline_obj = pooler.get_pool(self.cr.dbname).get('account.voucher.line')
        voucherlines = voucherline_obj.search(self.cr, self.uid,[('voucher_id','=',voucher.id)])
        voucherlines = voucherline_obj.browse(self.cr, self.uid, voucherlines)
        return voucherlines

    def _invoice_lines_get(self, voucher):
        invoice_line_obj = pooler.get_pool(self.cr.dbname).get('account.invoice.line')
        invoice_lines = invoice_line_obj.search(self.cr, self.uid,[('invoice_id','=',voucher.invoice_id.id)])
        invoice_lines = invoice_line_obj.browse(self.cr, self.uid, invoice_lines)
        return invoice_lines

    def _invoice_discount_get(self, voucher):
        discount = 0.0
        if(voucher.invoice_id):
            invoice = self._invoice_get(voucher.invoice_id.id)
            discount = invoice.discount
        return discount

    def _invoice_discount_head_get(self, voucher):
        disc_head = ''
        if(voucher.invoice_id):
            invoice = self._invoice_get(voucher.invoice_id.id)
            disc_account_obj = pooler.get_pool(self.cr.dbname).get('account.account')
            if(invoice.discount_acc_id):
                disc_account = disc_account_obj.browse(self.cr,self.uid,invoice.discount_acc_id.id)
                disc_head = disc_account.name
        return disc_head

    def _invoice_roundoff_get(self, voucher):
        round_off = 0.0
        if(voucher.invoice_id):
            invoice = self._invoice_get(voucher.invoice_id.id)
            round_off = invoice.round_off
        return round_off

    def _remove_internal_ref(self, name):
        name = re.sub(r"\[.*\]", "", name)
        return name

    def _invoice_get(self,invoice_id):
        invoice_obj = pooler.get_pool(self.cr.dbname).get('account.invoice')
        return invoice_obj.browse(self.cr, self.uid,invoice_id)


report_sxw.report_sxw('report.account_voucher', 'account.voucher',
                      'addons/print_receipt/reports/account_voucher.rml',
                      parser=account_voucher)
        
        
        
        