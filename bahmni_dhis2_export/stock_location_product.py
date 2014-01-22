import base64
import datetime
import logging
import operator

from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.addons.web.controllers.main import CSVExport

_logger = logging.getLogger(__name__)

class stock_location_product_dhis2(osv.osv_memory):
    _name = "stock.location.product.dhis2"
    _description = "DHIS2 Export product stock at location"

    MONTHS = [(1, "Jan"), (2, "Feb"), (3, "Mar"), (4, "Apr"), (5, "May"), (6, "Jun"), (7, "Jul"),
        (8, "Aug"), (9, "Sep"), (10, "Oct"), (11, "Nov"), (12, "Dec")]

    FIELDS = ['dhis2_code', 'virtual_available']
    HEADERS = ['dataelement', 'period', 'orgunit', 'categoryoptioncombo', 'value', 'storedby', 'lastupdated', 'comment', 'followup']

    def _get_default(self, cr, uid, context=None):
        one_month_ago = datetime.datetime.today() - relativedelta(months=1)
        last_month_tuple = [month for month in self.MONTHS if month[0] == one_month_ago.month]
        return {'month': last_month_tuple[0], 'year': one_month_ago.year}

    _columns = {
        'from_date': fields.datetime('From'),
        'to_date': fields.datetime('To'),
        'month': fields.selection(MONTHS, 'Month'),
        'year': fields.char('Year', size=4),
        'data': fields.binary('File', readonly=True),
        'name': fields.char('Filename', readonly=True),
        'state': fields.selection([('choose', 'choose'), ('get', 'get')]),
    }

    _defaults = {
        'state': 'choose',
        'name': 'stock_product_location.csv',
        'month': lambda self,cr,uid,c: self._get_default(cr,uid,c)['month'],
        'year': lambda self,cr,uid,c: self._get_default(cr,uid,c)['year'],
    }

    def action_generate_csv(self, cr, uid, ids, context=None):
        dialog_box_data = self.read(cr, uid, ids, ['month', 'year', 'to_date', 'from_date'], context=context)[0]
        export_data = self._get_export_data(cr, uid, dialog_box_data, context)
        csv_data = CSVExport().from_data(self.HEADERS, export_data)

        self.write(cr, uid, ids, {'data': base64.encodestring(csv_data), 'state': 'get'}, context=context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location.product.dhis2',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': ids[0],
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _get_export_data(self, cr, uid, dialog_box_data, context):
        product_model = self.pool.get('product.product')
        domain = [('type', '<>', 'service')]
        product_search_context = self._create_product_search_context(dialog_box_data, context=context)
        product_ids = product_model.search(cr, uid, domain, 0, False, False, context=product_search_context)

        export_data = product_model.export_data(cr, uid, product_ids, self.FIELDS, context=product_search_context).get('datas', [])
        orgunit = self._get_orgunit(cr, uid, context)
        period = self._get_first_day_of_month(dialog_box_data).strftime("%Y%m")
        modified_export_data = []
        for row in export_data:
            modified_row = []
            modified_row.append(row[0])  #dataelement
            modified_row.append(period)
            modified_row.append(orgunit)
            modified_row.append(None)   #categoryoptioncombo
            modified_row.append(row[1]) #value
            modified_row.append(None)   #storedby
            modified_row.append(None)   #lastupdated
            modified_row.append(None)   #comment
            modified_row.append(None)   #followup
            modified_export_data.append(modified_row)
        return modified_export_data


    def _create_product_search_context(self, data, context=None):
        return {
            'from_date': data['from_date'],
            'to_date': str(self._get_first_day_of_next_month(data)),
        }

    def _get_first_day_of_next_month(self, data):
        return self._get_first_day_of_month(data) + relativedelta(months=1)

    def _get_first_day_of_month(self, data):
        year = int(data['year'])
        month = int(data['month'])
        return datetime.datetime(year=year, month=month, day=1)

    def _get_orgunit(self, cr, uid, context):
        company_model = self.pool.get('res.company')
        company = company_model.browse(cr, uid, context['active_id'])
        return company.dhis2_code

stock_location_product_dhis2()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
