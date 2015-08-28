from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime

class average_sale_turn_around_time(osv.osv_memory):
    _name = "average_turn_around_time.report"
    _description = "Average Sales Turn Around Time"
    _columns = {
        'from_date': fields.datetime('From', required=True, store=False),
        'to_date': fields.datetime('To', required=True, store=False),
        'avg_billing': fields.float('Average between Quotation to sales order creation (mins)', store=False),
        'avg_pay': fields.float('Average between Sales order to receipt generation (sec)', store=False),
        'avg_total': fields.float('Average TAT Total (mins)', store=False),
    }

    def getAverage(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, ['to_date', 'from_date'], context=context)[0]
        sql = "select avg(bill_tat) as avg_billing, avg(pay_tat) as avg_pay, avg(total) as avg_total from turn_around_time_report where create_date BETWEEN '" + data['from_date'] + "' and '" + data['to_date'] + "'";
        cr.execute(sql);
        result = cr.fetchall();
        return self.write(cr, uid, ids, {'avg_billing': result[0][0], 'avg_pay': result[0][1], 'avg_total': result[0][2]}, context=context);

def unlink(self, cr, uid, ids, context=None):
    raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

average_sale_turn_around_time()
