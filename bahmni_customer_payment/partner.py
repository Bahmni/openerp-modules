import datetime
from lxml import etree
import math
import pytz
import re

import openerp
from openerp import SUPERUSER_ID
from openerp import pooler, tools
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _


import logging
_logger = logging.getLogger(__name__)

class format_address(object):
    def fields_view_get_address(self, cr, uid, arch, context={}):
        user_obj = self.pool.get('res.users')
        fmt = user_obj.browse(cr, SUPERUSER_ID, uid, context).company_id.country_id
        fmt = fmt and fmt.address_format
        layouts = {
            '%(city)s %(state_code)s\n%(zip)s': """
                <div class="address_format">
                    <field name="city" placeholder="City" style="width: 50%%"/>
                    <field name="state_id" class="oe_no_button" placeholder="State" style="width: 47%%" options='{"no_open": true}'/>
                    <br/>
                    <field name="zip" placeholder="ZIP"/>
                </div>
            """,
            '%(zip)s %(city)s': """
                <div class="address_format">
                    <field name="zip" placeholder="ZIP" style="width: 40%%"/>
                    <field name="city" placeholder="City" style="width: 57%%"/>
                    <br/>
                    <field name="state_id" class="oe_no_button" placeholder="State" options='{"no_open": true}'/>
                </div>
            """,
            '%(city)s\n%(state_name)s\n%(zip)s': """
                <div class="address_format">
                    <field name="city" placeholder="City"/>
                    <field name="state_id" class="oe_no_button" placeholder="State" options='{"no_open": true}'/>
                    <field name="zip" placeholder="ZIP"/>
                </div>
            """
        }
        for k,v in layouts.items():
            if fmt and (k in fmt):
                doc = etree.fromstring(arch)
                for node in doc.xpath("//div[@class='address_format']"):
                    tree = etree.fromstring(v)
                    node.getparent().replace(node, tree)
                arch = etree.tostring(doc)
                break
        return arch


def _tz_get(self,cr,uid, context=None):
    return [(x, x) for x in pytz.all_timezones]

class res_partner(osv.osv, format_address):
    _name = "res.partner"
    _inherit = "res.partner"

    _sql_constraints = [
        ('unique_ref', 'unique(ref)', 'The reference must be unique'),
    ]

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id:
                name =  "%s (%s)" % (name, record.parent_id.name)
            if(record.ref) :
                name = name+" ["+record.ref+"]"
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
                name = name.replace('\n\n','\n')
                name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        domain_expression = expression.expression(cr, uid, args, self, context)
        args_query_clause, args_query_params = domain_expression.to_sql()
        args_query_string = args_query_clause % tuple(args_query_params)

        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]
            query_args = {'name': search_name}
            limit_str = ''
            if limit:
                limit_str = ' limit %(limit)s'
                query_args['limit'] = limit

            cr.execute('''SELECT res_partner.id FROM res_partner
                          LEFT JOIN res_partner company ON res_partner.parent_id = company.id
                          WHERE (res_partner.email ''' + operator +''' %(name)s
                          OR res_partner.ref ''' + operator +''' %(name)s
                             OR res_partner.name || ' (' || COALESCE(company.name,'') || ')'
                          ''' + operator + ' %(name)s ) and ' + args_query_string + ' order by char_length(res_partner.ref) ' + limit_str, query_args)
            ids = map(lambda x: x[0], cr.fetchall())
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def name_create(self, cr, uid, name, context=None):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address. """
        if context is None:
            context = {}
        name, email = self._parse_partner_name(name, context=context)
        if context.get('force_email') and not email:
            raise osv.except_osv(_('Warning'), _("Couldn't create contact without email address !"))
        if not name and email:
            name = email
        rec_id = self.create(cr, uid, {self._rec_name: name or email, 'email': email or False}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]
res_partner()