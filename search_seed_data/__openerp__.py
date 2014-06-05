{
    "name": "Bahmni SEARCH Seed Data setup",
    "version": "1.0",
    "depends": ["base","product", "stock", "sale", "sale_stock", "bahmni_pharmacy_product"],
    "author": "ThoughtWorks Technologies Pvt. Ltd.",
    "category": "Setup",
	"summary": "Initial data setup",
    "description": """
    """,
    'data': [
        'data/settings.xml',
        'data/accounts_setup.xml',
        'data/product_category_setup.xml',
        'data/warehouse_seed_setup.xml',
        'data/unit_of_measures.xml',
        'data/products.xml',
    ],
    'demo': [],
    'auto_install': False,
    'application': True,
    'installable': True,
}
