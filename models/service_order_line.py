# -*- coding: utf-8 -*-
from odoo import models, fields

class ServiceOrderLine(models.Model):
    _name = 'service.order.line'
    _description = 'Línea de Orden de Servicio'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True
    )
    # Nota/descripcion que venga de la línea de venta
    name = fields.Text(
        string='Nota',
        help='Descripción o comentario que venía en la línea de la orden de venta'
    )
    product_uom_qty = fields.Float(
        string='Cantidad',
        default=1.0,
        required=True
    )
    product_uom = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        required=True
    )
    packaging_id = fields.Many2one(
        'product.packaging',
        string='Embalaje de Producto',
        help='Tipo de embalaje asociado al producto'
    )
    residue_type = fields.Selection(
        [
            ('rsu', 'RSU'),
            ('rme', 'RME'),
            ('rp', 'RP'),
        ],
        string='Tipo de Residuos'
    )
