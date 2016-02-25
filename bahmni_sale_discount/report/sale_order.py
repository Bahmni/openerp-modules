import time
from openerp.report import report_sxw


class sale_order_ext(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(sale_order_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            })

report_sxw.report_sxw('report.sale.order.sale_order_ext', 'sale.order', 'addons/bahmni_sale_discount/report/sale_order_ext.rml', parser=sale_order_ext, header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
