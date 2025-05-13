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
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
