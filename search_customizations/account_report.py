from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime, timedelta

class account_report(osv.osv):
    _name = "account.report"
    _description = "Account reports for actual & received amount"
    _auto = False
    _columns = {
        'actual_amount': fields.float('Expenses', readonly=True),
        'amount_received': fields.float('Collections', readonly=True),
        'date': fields.date('Date', readonly=True),
        'account_id': fields.many2one('account.account', 'Account Head', readonly=True, select=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'account_report')
        cr.execute("""
            create or replace view account_report as (
                select
                    concat(ail.account_id, '_', ai.date_invoice) as id,
                    ai.date_invoice as date,
                    ail.account_id as account_id,
                    sum(ail.price_subtotal) as actual_amount,
                    sum(ail.price_subtotal * (ai.amount_total/(ai.amount_tax + ai.amount_untaxed))) as amount_received
                from account_invoice ai, account_invoice_line ail
                where
                    ail.invoice_id = ai.id
                    and (ai.amount_tax + ai.amount_untaxed) > 0
                group by ail.account_id, ai.date_invoice
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

account_report()


class account_count_report(osv.osv):
    _name = "account.count.report"
    _description = "Count of account heads in sale orders over a period"
    _auto = False
    _columns = {
        'count': fields.integer('Count', readonly=True),
        'date': fields.date('Date', readonly=True),
        'account_id': fields.many2one('account.account', 'Account Head', readonly=True, select=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'account_count_report')
        cr.execute("""
            create or replace view account_count_report as (
                select
                    concat(ail.account_id, '_', ai.date_invoice) as id,
                    ai.date_invoice as date,
                    ail.account_id as account_id,
                    count(*) as count
                from account_invoice ai, account_invoice_line ail
                where
                    ail.invoice_id = ai.id
                group by ail.account_id, ai.date_invoice
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

account_count_report()