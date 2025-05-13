from odoo import models, fields

class ServiceOrderLine(models.Model):
    _name = 'service.order.line'
    _description = 'Línea de Orden de Servicio'

    service_order_id = fields.Many2one(
        'service.order', string='Orden de Servicio',
        required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True
    )
    product_uom_qty = fields.Float(
        string='Cantidad', default=1.0, required=True
    )
    product_uom = fields.Many2one(
        'uom.uom', string='Unidad de Medida', required=True
    )
    residue_type = fields.Selection(
        [('rsu', 'RSU'), ('rme', 'RME'), ('rp', 'RP')],
        string='Tipo de Residuos', required=False
    )
