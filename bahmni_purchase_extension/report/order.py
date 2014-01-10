import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler

class purchase_order_ext(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(purchase_order_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({'time': time})

report_sxw.report_sxw('report.purchase.purchase_order_ext', 'purchase.order', 'addons/bahmni_purchase_extension/report/purchase_order_ext.rml', parser=purchase_order_ext, header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

