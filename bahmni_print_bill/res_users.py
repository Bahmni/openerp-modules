import openerp
from openerp.osv import osv, fields

class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'

    _columns = {
        'initials': fields.char('Initials', size=10),
    }
