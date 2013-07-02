import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _

class res_partner(osv.osv):
    _description = 'Partner'
    _name = "res.partner"
    _inherit = "res.partner"

    _columns = {
        'village':fields.char('Village', size=64, help="Village of patient.",required=False),
     }