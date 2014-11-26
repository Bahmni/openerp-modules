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
        'actual_amount': fields.integer('Expenses', readonly=True),
        'amount_received': fields.integer('Collections', readonly=True),
        'date': fields.date('Date', readonly=True),
        'account_id': fields.many2one('account.account', 'Account Head', readonly=True, select=True),
    }


    def init(self, cr):
        drop_view_if_exists(cr, 'account_report')
        cr.execute("""
            create or replace view account_report as (
                (select id,date,account_id, sum(actual_amount) as actual_amount,sum(amount_received) as amount_received from (
                  SELECT
                    pg_catalog.concat(ail.account_id, '_', ai.date_invoice, '_', ai.type) AS id,
                    ai.date_invoice AS date,
                    ail.account_id,
                    CASE
                    WHEN ai.type = 'out_refund' THEN 0
                    ELSE sum(ail.price_subtotal * (ai.amount_total / (ai.amount_tax + ai.amount_untaxed)))
                    END AS actual_amount,
                    CASE
                    WHEN ai.type = 'out_refund' THEN sum(
                        (-ail.price_subtotal) * (ai.amount_total / (ai.amount_tax + ai.amount_untaxed)))
                    ELSE sum(ail.price_subtotal * (ai.amount_total / (ai.amount_tax + ai.amount_untaxed)))
                    END AS amount_received
                  FROM account_invoice ai, account_invoice_line ail
                  WHERE ail.invoice_id = ai.id AND (ai.amount_tax + ai.amount_untaxed) <> 0 AND state = 'paid'
                  GROUP BY ail.account_id, ai.date_invoice, ai.type
                  UNION
                  SELECT
                    pg_catalog.concat(ail.account_id, '_', ai.date_invoice, '_', ai.type) AS id,
                    ai.date_invoice AS date,
                    ail.account_id,
                    CASE
                    WHEN ai.type = 'out_refund' THEN 0
                    ELSE max(ai.amount_total)
                    END AS actual_amount,
                    CASE
                    WHEN ai.type = 'out_refund' THEN max(ai.amount_total) * -1
                    ELSE max(ai.amount_total)
                    END AS amount_received
                  FROM account_invoice ai, account_invoice_line ail
                  WHERE ail.invoice_id = ai.id AND (ai.amount_tax + ai.amount_untaxed) = 0 AND state = 'paid'
                        and ail.account_id not in
                        (select id from account_account where name in ('FINE','Discount','Overcharge'))
                  GROUP BY ail.account_id, ai.date_invoice, ai.type
                  UNION
                  SELECT
                    pg_catalog.concat(ail.account_id, '_', ai.date_invoice, '_', ai.type) AS id,
                    ai.date_invoice AS date,
                    ail.account_id,
                    CASE
                    WHEN ai.type = 'out_refund' THEN 0
                    ELSE sum(ai.amount_total)
                    END AS actual_amount,
                    CASE
                    WHEN ai.type = 'out_refund' THEN sum(-ai.amount_total)
                    ELSE sum(ai.amount_total)
                    END AS amount_received
                  FROM account_invoice ai, account_invoice_line ail
                  WHERE ail.invoice_id = ai.id AND (ai.amount_tax + ai.amount_untaxed) = 0 AND state = 'paid'
                        and ail.account_id in
                        (select id from account_account where name in ('FINE','Discount','Overcharge'))
                  GROUP BY ail.account_id, ai.date_invoice, ai.type
                ) as r group by id,date,account_id)
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
                    and ai.type != 'out_refund'
                group by ail.account_id, ai.date_invoice
            )""")

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('You cannot delete any record!'))

account_count_report()