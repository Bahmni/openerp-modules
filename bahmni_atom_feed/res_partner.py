from openerp.osv import fields,osv

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'local_name': fields.char('Local Name', size=128, required=False),
        'attributes': fields.one2many('res.partner.attributes', 'partner_id', 'Attributes'),
        'address': fields.one2many('res.partner.address', 'partner_id', 'Address')
    }


class res_partner_attributes(osv.osv):
    _name = 'res.partner.attributes'

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'value': fields.char('Value', required=False),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True, select=True, readonly=False)
    }

class res_partner_address(osv.osv):
    _name = 'res.partner.address'

    _columns = {
        'address1': fields.char('Address1', size=256, required=False),
        'address2': fields.char('Address2', size=256, required=False),
        'city_village': fields.char('City/Village', size=256, required=False),
        'state_province': fields.char('State/Province', size=256, required=False),
        'country': fields.char('Country', size=256, required=False),
        'county_district': fields.char('County/District', size=256, required=False),
        'address3': fields.char('Address3', size=256, required=False),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True, select=True, readonly=False)
    }

res_partner_attributes()
res_partner_address()
