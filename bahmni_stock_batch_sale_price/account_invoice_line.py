import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class account_invoice_line(osv.osv):
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"
    _columns = {
        # 'batch_id': fields.many2one('stock.production.lot', 'Batch No'),
        'batch_name': fields.char('Batch No'),
        'expiry_date': fields.char('Expiry Date'),
    }

account_invoice_line()