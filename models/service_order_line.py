# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ServiceOrderLine(models.Model):
    _name = 'service.order.line'
    _description = 'Línea de Orden de Servicio'

    service_order_id = fields.Many2one(
        'service.order', 'Orden de Servicio',
        required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', 'Residuo'
    )
    name = fields.Text(
        string='Equivalente',
        help='Descripción o comentario que venía en la línea de la orden de venta'
    )
    description = fields.Char(
        string='Residuo / Equivalente',
        compute='_compute_description',
        store=False
    )
    product_uom_qty = fields.Float('Cantidad', default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Unidad de Medida')
    packaging_id = fields.Many2one(
        'product.packaging', 'Embalaje de Producto',
        help='Tipo de embalaje asociado al producto'
    )
    residue_type = fields.Selection(
        [('rsu','RSU'),('rme','RME'),('rp','RP')],
        'Tipo de Residuos'
    )

    @api.depends('product_id', 'name')
    def _compute_description(self):
        for rec in self:
            if rec.product_id:
                rec.description = rec.product_id.display_name
            else:
                rec.description = rec.name or ''

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Si no hay producto (es nota), dejamos la cantidad en blanco
        if not self.product_id:
            self.product_uom_qty = False
