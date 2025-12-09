{
    'name': 'Service Order',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio independiente',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'account'],
    'data': [
        'security/security.xml',                            # 0. Security groups first
        'security/ir.model.access.csv',                     # 1. Access rights
        'views/service_order_views.xml',                    # 2. Vistas base (includes sequence)
        'reports/service_order_report.xml',                 # 3. Definición del reporte 
        'views/service_order_print_button.xml',             # 4. Botón que referencia el reporte
        'views/sale_order_inherit.xml',                     # 5. Resto de vistas
        'views/service_order_invoice_button.xml',
        'views/product_template_view.xml',
        'views/service_order_invoice_view_button.xml',
        'views/account_move_service_link_view.xml',
        'views/account_move_form_extension.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}