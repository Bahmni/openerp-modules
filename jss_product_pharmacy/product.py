
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class Pharmacy_Product(osv.osv):
    
    _name = 'product.product'
    _inherit = 'product.product'
    
    
    
    _columns = {
        
        'brand':fields.char('Brand', size=64),
			'manufacturer':fields.char('Manufacturer', size=64)
                
            }

Pharmacy_Product()
