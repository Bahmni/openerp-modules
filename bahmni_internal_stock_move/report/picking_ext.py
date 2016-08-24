
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from dateutil.tz import tzlocal,tzutc
from datetime import datetime

class picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_product_desc':self.get_product_desc,
            'get_formatted_date':self.get_formatted_date,
        })

    def get_formatted_date(self, date):
        utcdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=tzutc())
        localdate = utcdate.astimezone(tzlocal()).strftime('%m/%d/%Y %H:%M:%S')
        return localdate

    def get_product_desc(self,move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc


report_sxw.report_sxw('report.stock.picking.list_ext','stock.picking.in',
                      'addons/bahmni_internal_stock_move/report/picking_ext.rml',parser=picking)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: