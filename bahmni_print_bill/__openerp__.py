{
    "name": "Bahmni Print Bill",
    "version": "1.0",
    "depends": ["base","stock","bahmni_sale_discount", "bahmni_customer_payment"],
    "author": "ThoughtWorks Technologies Pvt. Ltd.",
    "category": "Sale",
    "summary": "Bahmni Batch Sale Price",
    "description": """
    """,
    'data': ["add_invoice_print_button.xml", "add_initials_to_res_users.xml"],
    'demo': [],
    'js': ['static/src/js/*.js'],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': False,
    'application': True,
    'installable': True,
#    'certificate': 'certificate',
}
