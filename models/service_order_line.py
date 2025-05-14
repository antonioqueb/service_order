# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ServiceOrderLine(models.Model):
    _name = 'service.order.line'
    _description = 'Línea de Orden de Servicio'

    service_order_id = fields.Many2one(
        'service.order', 'Orden de Servicio',
        required=True, ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', 'Residuo')
    name = fields.Text(
        string='Equivalente',
        help='Descripción o comentario que venía en la línea de la orden de venta'
    )
    description = fields.Char(
        string='Residuo / Equivalente',
        compute='_compute_description', store=False
    )

    # ▶  SIN default: así puede quedar realmente vacío (NULL) si es nota
    product_uom_qty = fields.Float('Cantidad')
    product_uom     = fields.Many2one('uom.uom', 'Unidad de Medida')

    packaging_id = fields.Many2one(
        'product.packaging', 'Embalaje de Producto',
        help='Tipo de embalaje asociado al producto'
    )
    residue_type = fields.Selection(
        [('rsu', 'RSU'), ('rme', 'RME'), ('rp', 'RP')],
        'Tipo de Residuos'
    )

    # ---------- Cálculos y validaciones ----------
    @api.depends('product_id', 'name')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.product_id.display_name if rec.product_id else (rec.name or '')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Si quitamos el producto (es nota) dejamos qty vacía.
        Si se selecciona un producto y no hay qty aún, ponemos 1."""
        for rec in self:
            if rec.product_id:
                if not rec.product_uom_qty:
                    rec.product_uom_qty = 1.0
                rec.product_uom = rec.product_id.uom_id
            else:
                rec.product_uom_qty = False
                rec.product_uom     = False

    @api.constrains('product_id', 'product_uom_qty')
    def _check_qty_for_products(self):
        """Obliga a poner cantidad > 0 cuando hay producto;
        permite qty vacía cuando es nota."""
        for rec in self:
            if rec.product_id and (not rec.product_uom_qty or rec.product_uom_qty <= 0):
                raise ValidationError(
                    _('Debe indicar una cantidad mayor a cero para las líneas con producto.')
                )
