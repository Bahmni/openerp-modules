from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = "account.voucher"


    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = super(account_voucher, self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        if(res.get('value', False) and res['value'].get('balance_amount', False)):
            res['value']['amount'] = res['value']['balance_amount']
        return res

