from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = "account.voucher"

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = super(account_voucher, self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
        if(res.get('value', False) and partner_id):
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            res['value']['amount'] = (partner.credit or partner.debit) if partner else 0.0
        return res

