from odoo import models, fields

class ServiceOrderLine(models.Model):
    _name = 'service.order.line'
    _description = 'Línea de Orden de Servicio'
    _inherits = {'sale.order.line': 'order_line_id'}

    order_line_id = fields.Many2one(
        'sale.order.line', required=True, ondelete='cascade',
        string='Línea de Cotización'
    )
    service_order_id = fields.Many2one(
        'service.order', required=True, ondelete='cascade',
        string='Orden de Servicio'
    )

    # Heredas todos los campos de sale.order.line, incluido residue_type
