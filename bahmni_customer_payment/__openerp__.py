{
    "name": "Bahmni Customer Payment",
    "version": "1.0",
    "depends": ["base","account", "account_voucher"],
    "author": "ThoughtWorks Technologies Pvt. Ltd.",
    "category": "Sale",
	"summary": "Customer Payment",
    "description": """
    """,
    'data': [
                "voucher_payment_receipt_view.xml",
                "show_creator_in_account_voucher_list.xml",
                "add_cashier_as_filter_group.xml",
                "customer_invoice_show_partner_reference.xml",
            ],
    'demo': [],
    'css' : [
        "static/src/css/voucher.css",
        ],

    'auto_install': False,
    'application': True,
    'installable': True,
#    'certificate': 'certificate',
}
