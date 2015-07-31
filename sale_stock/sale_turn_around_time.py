from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.sql import drop_view_if_exists
import logging


class sale_turn_around_time(osv.osv):
    _name = "turn_around_time.report"
    _description = "Sales Turn Around Time"
    _auto = False
    _order = 'id desc'
    _columns = {
        'patient_id': fields.text('Patient ID', readonly=True),
        'patient_name': fields.text('Patient Name', readonly=True),
        'create_date': fields.date('Invoice Date', readonly=True),
        'bill_tat': fields.float("TAT from billing to cashier window", readonly=True),
        'pay_tat': fields.float("TAT at cashier window", readonly=True),
        'total': fields.float("TAT total", readonly=True)
    }

    def _project_count(self):
        self.project_count = 100;

    project_count = fields.integer(compute="_project_count")

    def init(self, cr):
        drop_view_if_exists(cr, 'turn_around_time_report')
        cr.execute("""
            create or replace view turn_around_time_report as (
           select so.id, so.partner_id,rp.name patient_name,rp.ref patient_id,
    EXTRACT(EPOCH FROM (ao.create_date-so.create_date)) bill_tat,
    EXTRACT(EPOCH FROM (ao.write_date-ao.create_date)) pay_tat,
    (EXTRACT(EPOCH FROM (ao.create_date-so.create_date)) +
    EXTRACT(EPOCH FROM (ao.write_date-ao.create_date))
     ) as total,
    ao.create_date
  from sale_order so
  join account_invoice ao on so.name = ao.reference
  join res_partner rp on so.partner_id=rp.id
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))


sale_turn_around_time()
