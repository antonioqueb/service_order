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
    
    # SIN default: así puede quedar realmente vacío (NULL) si es nota
    product_uom_qty = fields.Float('Cantidad')
    product_uom = fields.Many2one('uom.uom', 'Unidad de Medida')
    
    # =========================================================
    # NUEVO: PRECIO Y MONEDA
    # =========================================================
    price_unit = fields.Float(
        string='Precio Unitario',
        digits='Product Price',
        default=0.0
    )
    
    # Campo auxiliar para saber la moneda (tomada de la cotización origen o de la compañía)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        compute='_compute_currency_id',
        store=True
    )

    @api.depends('service_order_id.sale_order_id', 'service_order_id.sale_order_id.currency_id')
    def _compute_currency_id(self):
        for line in self:
            if line.service_order_id.sale_order_id:
                line.currency_id = line.service_order_id.sale_order_id.currency_id
            else:
                line.currency_id = line.env.company.currency_id
    # =========================================================

    weight_kg = fields.Float(
        string='Peso Total (kg)',
        help='Peso total del residuo en kilogramos desde el lead/cotización'
    )
    
    capacity = fields.Char(
        string='Capacidad',
        help='Capacidad del contenedor (ej: 100 L, 200 Kg, 50 CM³)'
    )
    
    # --- CORRECCIÓN ODOO 19 ---
    # Cambiado product.packaging por uom.uom
    packaging_id = fields.Many2one(
        'uom.uom', 'Embalaje de Producto',
        help='Tipo de embalaje asociado al producto (gestionado como UoM en Odoo 19)'
    )
    # --------------------------

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
            ('relleno_sanitario', 'Relleno Sanitario'),
        ],
        string="Plan de Manejo",
        help="Método de tratamiento y/o disposición final para el residuo según normatividad ambiental."
    )

    @api.depends('product_id', 'name')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.product_id.display_name if rec.product_id else (rec.name or '')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Si quitamos el producto (es nota) dejamos qty vacía."""
        for rec in self:
            if rec.product_id:
                if not rec.product_uom_qty:
                    rec.product_uom_qty = 1.0
                rec.product_uom = rec.product_id.uom_id
                
                # Si hay cambio de producto manual, sugerimos su precio de lista
                # (Solo si no viene ya seteado de la venta)
                if not rec.price_unit:
                    rec.price_unit = rec.product_id.lst_price

                # --- CORRECCIÓN ODOO 19 ---
                if not rec.packaging_id:
                    # Búsqueda en uom.uom en lugar de packaging
                    packagings = self.env['uom.uom'].search([
                        ('product_id', '=', rec.product_id.id)
                    ], limit=1)
                    if packagings:
                        rec.packaging_id = packagings
            else:
                rec.product_uom_qty = False
                rec.product_uom = False
                rec.packaging_id = False
                rec.price_unit = 0.0
    
    @api.constrains('product_id', 'product_uom_qty')
    def _check_qty_for_products(self):
        for rec in self:
            if rec.product_id and (not rec.product_uom_qty or rec.product_uom_qty <= 0):
                raise ValidationError(
                    _('Debe indicar una cantidad mayor a cero para las líneas con producto.')
                )