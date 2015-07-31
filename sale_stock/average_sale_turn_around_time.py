from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
import logging


class average_sale_turn_around_time(osv.osv_memory):
    _name = "average_turn_around_time.report"
    _description = "Average Sales Turn Around Time",
    _columns = {
        'from_date': fields.datetime('From', required=True),
        'to_date': fields.datetime('To', required=True),
        'total': fields.float('Total')
    }

    def _project_count(self):
        self.project_count = 100;

    project_count = fields.integer(compute="_project_count")

    def yay(self, cr, uid, ids, context=None):
        logging.info("#######################################yay");
        data = self.read(cr, uid, ids, ['to_date', 'from_date'], context=context)[0]
        self.getAverage(cr, uid, ids, data);

    def getAverage(self, cr, uid, ids, data):
        sql = "select avg(bill_tat) as avg_billing, avg(pay_tat) as avg_pay from turn_around_time_report where create_date BETWEEN '" + data['from_date'] + "' and '" + data['to_date'] + "'";
        logging.info("sql =" + sql);
        cr.execute(sql);
        result = cr.fetchall();
        logging.info(result);
        return self.write(cr, uid, ids, {'total': result[0][0]});

    def init(self, cr):
        cr.execute("""
            CREATE TABLE average_turn_around_time_report (
              from_date        date,
              to_date   date,
              total     real
        )""")

def unlink(self, cr, uid, ids, context=None):
    raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))


average_sale_turn_around_time()
