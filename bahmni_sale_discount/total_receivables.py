import time
import datetime
from lxml import etree
import decimal_precision as dp

import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class total_receivables(osv.osv):

    _name = "account.receivables"
    _description = 'Total Receivables update service'

    #service method which used to be invoked during migration of patients to openmrs
    def update_customer_receivables(self, cr, uid, vals,context=None):
        patient_ref = vals[0][1]
        amount = vals[1][1]
        if(not amount):
            amount = 0.0
        if context is None:
            context = {}
            #disc_account = self.pool.get('account.account')
        amount_currency = 0.0
        date = time.strftime('%Y-%m-%d')
        period_obj = self.pool.get('account.period')
        period_ids = period_obj.find(cr, uid, date, context)
        period_id = period_ids and period_ids[0] or False
        acc_id = self.pool.get('account.account').search(cr, uid,[('name','=','Debtors')])[0]
        partner_id = self.pool.get('res.partner').search(cr, uid,[('ref','=',patient_ref)])[0]
        #company_id = self.pool.get('res.company').browse(cr, uid,uids)[0]

        l1 = {
            'debit': amount,
            'credit': 0,
            'account_id': acc_id,
            'partner_id': partner_id,
            'ref':"",
            'date': date,
            'period_id':period_id,
            #'currency_id':context['currency_id'],
            'amount_currency':amount_currency,
            'company_id': "1",
            'state': 'valid',
            }

        name = ""
        l1['name'] = name
        lines = [(0, 0, l1)]

        acc_journal_id = self.pool.get('account.journal').search(cr, uid,[('name','=','Cash')])[0]
        #acc_journal = self.pool.get('account.journal').browse(cr, uid,acc_journal_id)

        move = {'ref': "migration", 'line_id': lines, 'journal_id': acc_journal_id, 'period_id': period_id, 'date': date}
        move_ids =[]
        move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
        move_ids.append(move_id)
        obj_move_line = self.pool.get('account.move.line')
        line_ids=[]
        for move_new in self.pool.get('account.move').browse(cr,uid,move_ids,context=context):
            for line in move_new.line_id:
                line_ids.append(line.id)
            obj_move_line.write(cr, uid, line_ids,{
                'state': 'valid'
            }, context, check=False)
        return True


