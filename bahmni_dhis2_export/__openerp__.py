{
    "name": "Bahmni DHIS2 Stock Export",
    "version": "1.0",
    "depends": ["base","stock", "product"],
    "author": "ThoughtWorks Technologies Pvt. Ltd.",
    "category": "Sale",
    "summary": "Bahmni DHIS2 Stock Export",
    "description": """This module generates the csv stock report that can be imported in DHIS2.
    """,
    'data': ['dhis2_product_export.xml', 'add_dhis2_code_in_product.xml', 'add_dhis2_code_in_company.xml'],
    'demo': [],
    'auto_install': False,
    'application': True,
    'installable': True,
#    'certificate': 'certificate',
}
