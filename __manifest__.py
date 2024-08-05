{
    'name': 'Cash Register Management',
    'version': '14.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Module to manage cash register records',
    'description': """
Manage Cash Register
====================""",
    'author': 'ALIK Amrane',
    'depends': ['base', 'account', 'hr'],
    'data': [
        'views/cash_register_views.xml',
        'views/report_action.xml',
        'views/report_cash_register.xml',
        #'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
