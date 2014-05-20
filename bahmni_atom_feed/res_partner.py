from openerp.osv import fields,osv

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'local_name': fields.char('Local Name', size=128, required=False),
        'attributes': fields.one2many('res.partner.attributes', 'partner_id', 'Attributes')
    }


class res_partner_attributes(osv.osv):
    _name = 'res.partner.attributes'

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'value': fields.char('Value', required=False),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True, select=True, readonly=False)
    }   