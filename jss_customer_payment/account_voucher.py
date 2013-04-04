import time
from lxml import etree

from openerp import netsvc
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import float_compare

class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = "account.voucher"

    def _get_balance_amount(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        currency_obj = self.pool.get('res.currency')
        res = {}
        amount_unreconciled = 0.0
        for voucher in self.browse(cr, uid, ids, context=context):
            sign = voucher.type == 'payment' and -1 or 1
            for l in voucher.line_dr_ids:
                amount_unreconciled +=l.amount_unreconciled
            for l in voucher.line_cr_ids:
                amount_unreconciled +=l.amount_unreconciled
            currency = voucher.currency_id or voucher.company_id.currency_id
            res[voucher.id] =  currency_obj.round(cr, uid, currency, amount_unreconciled - voucher.amount)
        return res


    _columns={

        'balance_amount': fields.function(_get_balance_amount, string='Total Balance', type='float', readonly=True, help="Total Receivables"),

    }
