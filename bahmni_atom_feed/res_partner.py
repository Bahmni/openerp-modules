from openerp.osv import fields,osv

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'local_name': fields.char('Local Name', size=128, required=False),
    }