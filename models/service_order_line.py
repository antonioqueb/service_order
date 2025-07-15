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
    
    # ▶ SIN default: así puede quedar realmente vacío (NULL) si es nota
    product_uom_qty = fields.Float('Cantidad')
    product_uom = fields.Many2one('uom.uom', 'Unidad de Medida')
    
    # NUEVO: Campo para almacenar el peso en kg desde el CRM lead
    weight_kg = fields.Float(
        string='Peso Total (kg)',
        help='Peso total del residuo en kilogramos desde el lead/cotización'
    )
    
    packaging_id = fields.Many2one(
        'product.packaging', 'Embalaje de Producto',
        help='Tipo de embalaje asociado al producto'
    )
    residue_type = fields.Selection(
        [('rsu', 'RSU'), ('rme', 'RME'), ('rp', 'RP')],
        'Tipo de Residuos'
    )
    plan_manejo = fields.Selection(
        selection=[
            ('reciclaje', 'Reciclaje'),
            ('coprocesamiento', 'Co-procesamiento'),
            ('tratamiento_fisicoquimico', 'Tratamiento Físico-Químico'),
            ('tratamiento_biologico', 'Tratamiento Biológico'),
            ('tratamiento_termico', 'Tratamiento Térmico (Incineración)'),
            ('confinamiento_controlado', 'Confinamiento Controlado'),
            ('reutilizacion', 'Reutilización'),
            ('destruccion_fiscal', 'Destrucción Fiscal'),
        ],
        string="Plan de Manejo",
        help="Método de tratamiento y/o disposición final para el residuo según normatividad ambiental."
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
                # Buscar un embalaje por defecto para el producto
                if not rec.packaging_id:
                    default_packaging = rec.product_id.packaging_ids.filtered('is_default')[:1]
                    if not default_packaging:
                        default_packaging = rec.product_id.packaging_ids[:1]
                    rec.packaging_id = default_packaging
            else:
                rec.product_uom_qty = False
                rec.product_uom = False
                rec.packaging_id = False
    
    @api.constrains('product_id', 'product_uom_qty')
    def _check_qty_for_products(self):
        """Obliga a poner cantidad > 0 cuando hay producto;
        permite qty vacía cuando es nota."""
        for rec in self:
            if rec.product_id and (not rec.product_uom_qty or rec.product_uom_qty <= 0):
                raise ValidationError(
                    _('Debe indicar una cantidad mayor a cero para las líneas con producto.')
                )