import logging
import operator
import simplejson
import openerp
import openerp.modules.registry

from web.controllers.main import CSVExport
from web.controllers.main import content_disposition
from web import http as openerpweb

_logger = logging.getLogger(__name__)

class CSVExportExtension(CSVExport):

    @openerpweb.httprequest
    def index(self, req, data, token):
        model, fields, ids, domain, import_compat, context = \
            operator.itemgetter('model', 'fields', 'ids', 'domain',
                                'import_compat', 'context')(
                simplejson.loads(data))
        Model = req.session.model(model)
        ids = ids or Model.search(domain, 0, False, False, context)

        field_names = map(operator.itemgetter('name'), fields)
        import_data = Model.export_data(ids, field_names, context).get('datas',[])

        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        return req.make_response(self.from_data(columns_headers, import_data),
            headers=[('Content-Disposition',
                            content_disposition(self.filename(model), req)),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': int(token)})
