{
    "name": "Bahmni Internal Stock Move",
    "version": "1.0",
    "depends": ["base","stock"],
    "author": "ThoughtWorks Technologies Pvt. Ltd.",
    "category": "Stock",
    "summary": "Stock internal move",
    "description": """
    """,
    'data': [
        'security/ir.model.access.csv',
        'stock_internal_move_view.xml',
        'stock_location_prod_lot_view.xml',
        'stock_view.xml',
        'stock_move_view.xml'
    ],
    'demo': [],
    'auto_install': False,
    'application': True,
    'installable': True,
}
