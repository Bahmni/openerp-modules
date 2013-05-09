# -*- encoding: utf-8 -*-
{
    'name' : 'TS - Print Receipt',
    'version' : '1.0',
    'category' : 'Extra Reports',
    'author'  : 'Anas Taji',
    'license' : 'AGPL-3',
    'depends' : ['account_accountant', ],
    'update_xml' : ['print_receipt_reports.xml','voucher_payment_receipt_view.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': '''
This module adds the following reports:
============================================================
  1- Sales Receipts
  2- Customer Payments
  3- Purchase Receipts
  4- Supplier Payments
    '''
}
