from openerp.osv import fields, osv

class syncable_units(osv.osv):
    _name = "syncable.units"
    _description = "Units allowed to Sync as it is"
    _columns = {
        'name': fields.char('Units Name', required=True),
    }

syncable_units()
