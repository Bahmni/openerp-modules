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
        invoice_obj = pooler.get_pool(self.cr.dbname).get('account.invoice')
        invoice = invoice_obj.browse(self.cr, self.uid,voucher.invoice_id.id)
        return invoice.discount

    def _invoice_roundoff_get(self, voucher):
        invoice_obj = pooler.get_pool(self.cr.dbname).get('account.invoice')
        invoice = invoice_obj.browse(self.cr, self.uid,voucher.invoice_id.id)
        return invoice.round_off

    def _remove_internal_ref(self, name):
        name = re.sub(r"<\[*\]", "", name)
        return name

report_sxw.report_sxw('report.account_voucher', 'account.voucher',
                      'addons/print_receipt/reports/account_voucher.rml',
                      parser=account_voucher)
        
        
        
        