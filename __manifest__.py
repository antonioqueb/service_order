{
    'name': 'Service Order',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio independiente',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/service_order_views.xml',
        'views/sale_order_inherit.xml',
        'views/service_order_invoice_button.xml',
        'views/service_order_invoice_view_button.xml',
        'views/account_move_service_link_view.xml',
        'views/service_order_views.xml',
        'views/account_move_form_extension.xml',

    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
