{
    'name': 'Service Order',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio (hereda sale.order)',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'crm_custom_fields'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/service_order_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
