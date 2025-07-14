-e ### ./models/account_move_service_link.py
```
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio',
        readonly=True,
        copy=False,
        help='Orden de Servicio origen de esta factura'
    )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
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

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        # Llamamos al método original para crear la factura
        action = super(ServiceOrder, self).action_create_invoice()
        invoice = self.env['account.move'].browse(action.get('res_id'))
        # Escribimos el vínculo con esta orden de servicio
        if invoice:
            invoice.write({'service_order_id': self.id})
        return action
```

-e ### ./models/product_extension.py
```
# models/product_extension.py - NUEVO ARCHIVO en módulo service_order

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    clasificacion_residuo = fields.Selection([
        ('biologico_infeccioso', 'Biológico-Infeccioso'),
        ('corrosivo', 'Corrosivo'),
        ('reactivo', 'Reactivo'),
        ('explosivo', 'Explosivo'),
        ('toxico', 'Tóxico'),
        ('inflamable', 'Inflamable'),
        ('biologico', 'Biológico'),
    ], string='Clasificación del Residuo')
    
    envase_tipo_default = fields.Selection([
        ('tambor', 'Tambor'),
        ('contenedor', 'Contenedor'),
        ('tote', 'Tote'),
        ('tarima', 'Tarima'),
        ('saco', 'Saco'),
        ('caja', 'Caja'),
        ('bolsa', 'Bolsa'),
        ('tanque', 'Tanque'),
        ('otro', 'Otro'),
    ], string='Tipo de Envase por Defecto')
    
    envase_capacidad_default = fields.Float(
        string='Capacidad de Envase por Defecto',
        help='Capacidad del envase en la unidad correspondiente'
    )
```

-e ### ./models/sale_order_extension.py
```
# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id':    self.partner_id.id,
            'date_order':    fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),
            'pickup_location': getattr(self, 'pickup_location', False),
        })
        
        # 2) Copiar líneas - ahora solo servicios reales
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
                }
                self.env['service.order.line'].create(vals)
        
        # 3) Abrir la vista en modo formulario
        return {
            'name':      'Orden de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id':    service.id,
            'target':    'current',
        }

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name':   f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action
```

-e ### ./models/service_order_invoice_view.py
```
# models/service_order_invoice_view.py
from odoo import models, fields, api

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_metrics'
    )

    @api.depends('name')
    def _compute_invoice_metrics(self):
        for rec in self:
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', rec.name),
                ('move_type', '=', 'out_invoice'),
            ])
            rec.invoice_count = len(invoices)

    def action_view_linked_invoices(self):
        self.ensure_one()
        domain = [
            ('invoice_origin', '=', self.name),
            ('move_type', '=', 'out_invoice'),
        ]
        # Reusa la acción de cliente (facturas) de account
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action.update({
            'domain': domain,
            'name': 'Facturas de Servicio',
        })
        return action
```

-e ### ./models/service_order_invoice.py
```
from odoo import models, fields
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        self.ensure_one()
        # Asegúrate de que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError("No hay líneas de producto que facturar.")

        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
        }

        # Recorre TODAS las líneas en el orden original
        for line in self.line_ids:
            if line.product_id:
                # Línea de producto
                price = line.product_id.lst_price or 0.0
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id':     line.product_id.id,
                    'quantity':       line.product_uom_qty,
                    'price_unit':     price,
                    'name':           line.product_id.display_name,
                    'tax_ids':        [(6, 0, line.product_id.taxes_id.ids)],
                    'product_uom_id': line.product_uom.id,
                    'plan_manejo':    line.plan_manejo,
                }))
            else:
                # Línea de nota nativa en la factura
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         line.description or '',
                }))

        invoice = self.env['account.move'].create(invoice_vals)
        return {
            'name':      'Factura de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }
```

-e ### ./models/service_order_line.py
```
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

    # Campo computado para mostrar la unidad correcta en reportes
    display_uom = fields.Char(
        string='Unidad para Reporte',
        compute='_compute_display_uom',
        help='Muestra el embalaje si existe, sino la unidad de medida'
    )

# ---------- Cálculos y validaciones ----------
    @api.depends('product_id', 'name')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.product_id.display_name if rec.product_id else (rec.name or '')

    @api.depends('packaging_id', 'product_uom')
    def _compute_display_uom(self):
        """Computa la unidad a mostrar: embalaje si existe, sino unidad estándar"""
        for rec in self:
            if rec.packaging_id:
                rec.display_uom = rec.packaging_id.name
            elif rec.product_uom:
                rec.display_uom = rec.product_uom.name
            else:
                rec.display_uom = ''

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
                rec.product_uom     = False
                rec.packaging_id    = False

    @api.constrains('product_id', 'product_uom_qty')
    def _check_qty_for_products(self):
        """Obliga a poner cantidad > 0 cuando hay producto;
        permite qty vacía cuando es nota."""
        for rec in self:
            if rec.product_id and (not rec.product_uom_qty or rec.product_uom_qty <= 0):
                raise ValidationError(
                    _('Debe indicar una cantidad mayor a cero para las líneas con producto.')
                )
```

-e ### ./models/service_order.py
```
from odoo import models, fields, api
from datetime import date

class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Orden de Servicio'

    name = fields.Char(
        string='Referencia', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('service.order')
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Contrato de Venta',
        required=True, ondelete='restrict'
    )
    partner_id = fields.Many2one(
        'res.partner', string='Cliente',
        required=True
    )
    date_order = fields.Datetime(
        string='Fecha Pedido', default=fields.Datetime.now,
        required=True
    )
    expiration_date = fields.Date(
        string='Fecha Expiración',
        default=lambda self: date(date.today().year, 12, 31),
        required=True
    )
    service_frequency = fields.Char(string='Frecuencia del Servicio')
    residue_new = fields.Boolean(string='¿Residuo Nuevo?')
    requiere_visita = fields.Boolean(string='Requiere visita presencial')
    pickup_location = fields.Char(string='Ubicación de recolección')

    # Campos adicionales
    generador_id = fields.Many2one(
        'res.partner', string='Generador'
    )
    contact_name = fields.Char(
        string='Nombre de contacto'
    )
    contact_phone = fields.Char(
        string='Teléfono de contacto'
    )
    transportista_id = fields.Many2one(
        'res.partner', string='Transportista'
    )
    # Campos de transporte como Char en lugar de fleet.vehicle
    camion = fields.Char(string='Camión')
    chofer_id = fields.Many2one(
        'res.partner', string='Chofer'
    )
    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')
    numero_bascula = fields.Char(
        string='Número de báscula'
    )
    
    # Nuevos campos para sincronización con manifiesto
    numero_placa = fields.Char(
        string='Número de Placa',
        help='Número de placa del vehículo de transporte'
    )
    
    generador_responsable = fields.Char(
        string='Responsable del Generador',
        help='Persona responsable en el sitio del generador'
    )
    
    transportista_responsable = fields.Char(
        string='Responsable del Transportista', 
        help='Persona responsable del transportista'
    )
    
    destinatario_id = fields.Many2one(
        'res.partner',
        string='Destinatario Final',
        help='Empresa destinataria final de los residuos'
    )

    # Campo para observaciones
    observaciones = fields.Text(
        string='Observaciones',
        help='Observaciones adicionales sobre la orden de servicio'
    )

    line_ids = fields.One2many(
        'service.order.line', 'service_order_id',
        string='Líneas de Servicio'
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_set_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
```

-e ### ./reports/service_order_report.xml
```
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Definición del reporte -->
    <record id="action_report_service_order" model="ir.actions.report">
        <field name="name">Orden de Servicio</field>
        <field name="model">service.order</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">service_order.service_order_document</field>
        <field name="report_file">service_order.service_order_document</field>
        <field name="binding_model_id" ref="model_service_order"/>
        <field name="binding_type">report</field>
    </record>

    <!-- Template del reporte -->
    <template id="service_order_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <div class="oe_structure"/>
                        
                        <!-- Encabezado compacto -->
                        <div class="row mb16">
                            <div class="col-12">
                                <h4 class="mb8 text-primary">ORDEN DE SERVICIO N° <span t-field="doc.name"/></h4>
                            </div>
                        </div>
                        
                        <!-- Tabla única con toda la información -->
                        <table class="table table-sm table-bordered mb16" style="font-size: 11px;">
                            <tr>
                                <td style="width: 15%; background-color: rgb(233, 233, 233);"><strong>Cliente</strong></td>
                                <td style="width: 35%;"><span t-field="doc.partner_id.name"/></td>
                                <td style="width: 15%; background-color: rgb(233, 233, 233);"><strong>Transportista</strong></td>
                                <td style="width: 35%;"><span t-field="doc.transportista_id.name"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Generador</strong></td>
                                <td><span t-field="doc.generador_id.name"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Camión</strong></td>
                                <td><span t-field="doc.camion"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Dirección</strong></td>
                                <td>
                                    <div t-field="doc.partner_id" 
                                         t-options='{"widget": "contact", "fields": ["address"], "no_marker": True}'/>
                                </td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Chofer</strong></td>
                                <td><span t-field="doc.chofer_id.name"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Contacto</strong></td>
                                <td>
                                    <span t-field="doc.contact_name"/>
                                    <span t-if="doc.contact_phone"> - <span t-field="doc.contact_phone"/></span>
                                </td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Remolque 1</strong></td>
                                <td><span t-field="doc.remolque1"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Ubicación</strong></td>
                                <td><span t-field="doc.pickup_location"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Remolque 2</strong></td>
                                <td><span t-field="doc.remolque2"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Fecha de Servicio</strong></td>
                                <td><span t-field="doc.date_order" t-options='{"widget": "date"}'/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>N° de Báscula</strong></td>
                                <td style="height: 25px; background-color: #fff;">
                                    <span t-if="doc.numero_bascula" t-field="doc.numero_bascula"/>
                                    <span t-if="not doc.numero_bascula" style="color: #ccc;">_________________</span>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Estado</strong></td>
                                <td><span t-field="doc.state"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Cotización</strong></td>
                                <td><span t-field="doc.sale_order_id.name"/></td>
                            </tr>
                        </table>

                        <!-- Líneas de Servicio -->
                        <table class="table table-sm table-bordered mb16" style="font-size: 10px;">
                            <thead style="background-color: rgb(233, 233, 233);">
                                <tr>
                                    <th style="width: 35%;" class="text-left">Descripción</th>
                                    <th style="width: 12%;" class="text-right">Cantidad</th>
                                    <th style="width: 20%;" class="text-center">Unidad</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="doc.line_ids" t-as="line">
                                    <tr>
                                        <td style="font-size: 10px;">
                                            <span t-if="line.product_id" t-field="line.product_id.name"/>
                                            <span t-if="not line.product_id" t-field="line.name"/>
                                        </td>
                                       
                                        <td class="text-right" style="font-size: 10px;">
                                            <span t-if="line.product_id and line.product_uom_qty" t-field="line.product_uom_qty"/>
                                        </td>
                                        <td class="text-center" style="font-size: 10px;">
                                            <span t-if="line.packaging_id" t-field="line.packaging_id.name"/>
                                            <span t-if="not line.packaging_id and line.product_uom" t-field="line.product_uom.name"/>
                                        </td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>

                        <!-- Sección de OBSERVACIONES -->
                        <div class="mb32">
                            <table class="table table-bordered" style="margin-bottom: 20px;">
                                <tr>
                                    <td style="background-color: rgb(233, 233, 233); text-align: center; font-weight: bold; padding: 8px;">
                                        OBSERVACIONES
                                    </td>
                                </tr>
                                <tr>
                                    <td style="min-height: 80px; padding: 10px; font-size: 11px; vertical-align: top;">
                                        <span t-if="doc.observaciones" t-field="doc.observaciones"/>
                                        <span t-if="not doc.observaciones" style="color: #ccc; font-style: italic;">
                                            Sin observaciones registradas
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- Sección de FIRMAS -->
                        <div style="margin-top: 40px;">
                            <table class="table table-bordered" style="width: 100%;">
                                <tr>
                                    <!-- Columna Firma del Cliente -->
                                    <td style="width: 50%; padding: 0; vertical-align: top;">
                                        <table style="width: 100%; height: 140px; border: none;">
                                            <tr>
                                                <td style="text-align: center; font-weight: bold; background-color: rgb(233, 233, 233); padding: 8px; border: 1px solid #000;">
                                                    FIRMA DEL CLIENTE
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="height: 100px; border: 1px solid #000; border-top: none; background-color: #fff;">
                                                    <!-- Espacio en blanco para firma -->
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <!-- Columna Firma del Chofer -->
                                    <td style="width: 50%; padding: 0; vertical-align: top;">
                                        <table style="width: 100%; height: 140px; border: none;">
                                            <tr>
                                                <td style="text-align: center; font-weight: bold; background-color: rgb(233, 233, 233); padding: 8px; border: 1px solid #000;">
                                                    FIRMA DEL CHOFER
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="height: 100px; border: 1px solid #000; border-top: none; background-color: #fff;">
                                                    <!-- Espacio en blanco para firma -->
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <div class="oe_structure"/>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

-e ### ./salida_modulo_completo.md
```
-e ### ./models/account_move_service_link.py
```
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio',
        readonly=True,
        copy=False,
        help='Orden de Servicio origen de esta factura'
    )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
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

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        # Llamamos al método original para crear la factura
        action = super(ServiceOrder, self).action_create_invoice()
        invoice = self.env['account.move'].browse(action.get('res_id'))
        # Escribimos el vínculo con esta orden de servicio
        if invoice:
            invoice.write({'service_order_id': self.id})
        return action
```

-e ### ./models/product_extension.py
```
# models/product_extension.py - NUEVO ARCHIVO en módulo service_order

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    clasificacion_residuo = fields.Selection([
        ('biologico_infeccioso', 'Biológico-Infeccioso'),
        ('corrosivo', 'Corrosivo'),
        ('reactivo', 'Reactivo'),
        ('explosivo', 'Explosivo'),
        ('toxico', 'Tóxico'),
        ('inflamable', 'Inflamable'),
        ('biologico', 'Biológico'),
    ], string='Clasificación del Residuo')
    
    envase_tipo_default = fields.Selection([
        ('tambor', 'Tambor'),
        ('contenedor', 'Contenedor'),
        ('tote', 'Tote'),
        ('tarima', 'Tarima'),
        ('saco', 'Saco'),
        ('caja', 'Caja'),
        ('bolsa', 'Bolsa'),
        ('tanque', 'Tanque'),
        ('otro', 'Otro'),
    ], string='Tipo de Envase por Defecto')
    
    envase_capacidad_default = fields.Float(
        string='Capacidad de Envase por Defecto',
        help='Capacidad del envase en la unidad correspondiente'
    )
```

-e ### ./models/sale_order_extension.py
```
# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id':    self.partner_id.id,
            'date_order':    fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),
            'pickup_location': getattr(self, 'pickup_location', False),
        })
        
        # 2) Copiar líneas - ahora solo servicios reales
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
                }
                self.env['service.order.line'].create(vals)
        
        # 3) Abrir la vista en modo formulario
        return {
            'name':      'Orden de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id':    service.id,
            'target':    'current',
        }

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name':   f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action
```

-e ### ./models/service_order_invoice_view.py
```
# models/service_order_invoice_view.py
from odoo import models, fields, api

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_metrics'
    )

    @api.depends('name')
    def _compute_invoice_metrics(self):
        for rec in self:
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', rec.name),
                ('move_type', '=', 'out_invoice'),
            ])
            rec.invoice_count = len(invoices)

    def action_view_linked_invoices(self):
        self.ensure_one()
        domain = [
            ('invoice_origin', '=', self.name),
            ('move_type', '=', 'out_invoice'),
        ]
        # Reusa la acción de cliente (facturas) de account
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action.update({
            'domain': domain,
            'name': 'Facturas de Servicio',
        })
        return action
```

-e ### ./models/service_order_invoice.py
```
from odoo import models, fields
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        self.ensure_one()
        # Asegúrate de que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError("No hay líneas de producto que facturar.")

        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
        }

        # Recorre TODAS las líneas en el orden original
        for line in self.line_ids:
            if line.product_id:
                # Línea de producto
                price = line.product_id.lst_price or 0.0
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id':     line.product_id.id,
                    'quantity':       line.product_uom_qty,
                    'price_unit':     price,
                    'name':           line.product_id.display_name,
                    'tax_ids':        [(6, 0, line.product_id.taxes_id.ids)],
                    'product_uom_id': line.product_uom.id,
                    'plan_manejo':    line.plan_manejo,
                }))
            else:
                # Línea de nota nativa en la factura
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         line.description or '',
                }))

        invoice = self.env['account.move'].create(invoice_vals)
        return {
            'name':      'Factura de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }
```

-e ### ./models/service_order_line.py
```
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

    # Campo computado para mostrar la unidad correcta en reportes
    display_uom = fields.Char(
        string='Unidad para Reporte',
        compute='_compute_display_uom',
        help='Muestra el embalaje si existe, sino la unidad de medida'
    )

# ---------- Cálculos y validaciones ----------
    @api.depends('product_id', 'name')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.product_id.display_name if rec.product_id else (rec.name or '')

    @api.depends('packaging_id', 'product_uom')
    def _compute_display_uom(self):
        """Computa la unidad a mostrar: embalaje si existe, sino unidad estándar"""
        for rec in self:
            if rec.packaging_id:
                rec.display_uom = rec.packaging_id.name
            elif rec.product_uom:
                rec.display_uom = rec.product_uom.name
            else:
                rec.display_uom = ''

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
                rec.product_uom     = False
                rec.packaging_id    = False

    @api.constrains('product_id', 'product_uom_qty')
    def _check_qty_for_products(self):
        """Obliga a poner cantidad > 0 cuando hay producto;
        permite qty vacía cuando es nota."""
        for rec in self:
            if rec.product_id and (not rec.product_uom_qty or rec.product_uom_qty <= 0):
                raise ValidationError(
                    _('Debe indicar una cantidad mayor a cero para las líneas con producto.')
                )
```

-e ### ./models/service_order.py
```
from odoo import models, fields, api
from datetime import date

class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Orden de Servicio'

    name = fields.Char(
        string='Referencia', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('service.order')
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Contrato de Venta',
        required=True, ondelete='restrict'
    )
    partner_id = fields.Many2one(
        'res.partner', string='Cliente',
        required=True
    )
    date_order = fields.Datetime(
        string='Fecha Pedido', default=fields.Datetime.now,
        required=True
    )
    expiration_date = fields.Date(
        string='Fecha Expiración',
        default=lambda self: date(date.today().year, 12, 31),
        required=True
    )
    service_frequency = fields.Char(string='Frecuencia del Servicio')
    residue_new = fields.Boolean(string='¿Residuo Nuevo?')
    requiere_visita = fields.Boolean(string='Requiere visita presencial')
    pickup_location = fields.Char(string='Ubicación de recolección')

    # Campos adicionales
    generador_id = fields.Many2one(
        'res.partner', string='Generador'
    )
    contact_name = fields.Char(
        string='Nombre de contacto'
    )
    contact_phone = fields.Char(
        string='Teléfono de contacto'
    )
    transportista_id = fields.Many2one(
        'res.partner', string='Transportista'
    )
    # Campos de transporte como Char en lugar de fleet.vehicle
    camion = fields.Char(string='Camión')
    chofer_id = fields.Many2one(
        'res.partner', string='Chofer'
    )
    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')
    numero_bascula = fields.Char(
        string='Número de báscula'
    )
    
    # Nuevos campos para sincronización con manifiesto
    numero_placa = fields.Char(
        string='Número de Placa',
        help='Número de placa del vehículo de transporte'
    )
    
    generador_responsable = fields.Char(
        string='Responsable del Generador',
        help='Persona responsable en el sitio del generador'
    )
    
    transportista_responsable = fields.Char(
        string='Responsable del Transportista', 
        help='Persona responsable del transportista'
    )
    
    destinatario_id = fields.Many2one(
        'res.partner',
        string='Destinatario Final',
        help='Empresa destinataria final de los residuos'
    )

    # Campo para observaciones
    observaciones = fields.Text(
        string='Observaciones',
        help='Observaciones adicionales sobre la orden de servicio'
    )

    line_ids = fields.One2many(
        'service.order.line', 'service_order_id',
        string='Líneas de Servicio'
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_set_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
```

-e ### ./reports/service_order_report.xml
```
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Definición del reporte -->
    <record id="action_report_service_order" model="ir.actions.report">
        <field name="name">Orden de Servicio</field>
        <field name="model">service.order</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">service_order.service_order_document</field>
        <field name="report_file">service_order.service_order_document</field>
        <field name="binding_model_id" ref="model_service_order"/>
        <field name="binding_type">report</field>
    </record>

    <!-- Template del reporte -->
    <template id="service_order_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <div class="oe_structure"/>
                        
                        <!-- Encabezado compacto -->
                        <div class="row mb16">
                            <div class="col-12">
                                <h4 class="mb8 text-primary">ORDEN DE SERVICIO N° <span t-field="doc.name"/></h4>
                            </div>
                        </div>
                        
                        <!-- Tabla única con toda la información -->
                        <table class="table table-sm table-bordered mb16" style="font-size: 11px;">
                            <tr>
                                <td style="width: 15%; background-color: rgb(233, 233, 233);"><strong>Cliente</strong></td>
                                <td style="width: 35%;"><span t-field="doc.partner_id.name"/></td>
                                <td style="width: 15%; background-color: rgb(233, 233, 233);"><strong>Transportista</strong></td>
                                <td style="width: 35%;"><span t-field="doc.transportista_id.name"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Generador</strong></td>
                                <td><span t-field="doc.generador_id.name"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Camión</strong></td>
                                <td><span t-field="doc.camion"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Dirección</strong></td>
                                <td>
                                    <div t-field="doc.partner_id" 
                                         t-options='{"widget": "contact", "fields": ["address"], "no_marker": True}'/>
                                </td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Chofer</strong></td>
                                <td><span t-field="doc.chofer_id.name"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Contacto</strong></td>
                                <td>
                                    <span t-field="doc.contact_name"/>
                                    <span t-if="doc.contact_phone"> - <span t-field="doc.contact_phone"/></span>
                                </td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Remolque 1</strong></td>
                                <td><span t-field="doc.remolque1"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Ubicación</strong></td>
                                <td><span t-field="doc.pickup_location"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Remolque 2</strong></td>
                                <td><span t-field="doc.remolque2"/></td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Fecha de Servicio</strong></td>
                                <td><span t-field="doc.date_order" t-options='{"widget": "date"}'/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>N° de Báscula</strong></td>
                                <td style="height: 25px; background-color: #fff;">
                                    <span t-if="doc.numero_bascula" t-field="doc.numero_bascula"/>
                                    <span t-if="not doc.numero_bascula" style="color: #ccc;">_________________</span>
                                </td>
                            </tr>
                            <tr>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Estado</strong></td>
                                <td><span t-field="doc.state"/></td>
                                <td style="background-color: rgb(233, 233, 233);"><strong>Cotización</strong></td>
                                <td><span t-field="doc.sale_order_id.name"/></td>
                            </tr>
                        </table>

                        <!-- Líneas de Servicio -->
                        <table class="table table-sm table-bordered mb16" style="font-size: 10px;">
                            <thead style="background-color: rgb(233, 233, 233);">
                                <tr>
                                    <th style="width: 35%;" class="text-left">Descripción</th>
                                    <th style="width: 12%;" class="text-right">Cantidad</th>
                                    <th style="width: 20%;" class="text-center">Unidad</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="doc.line_ids" t-as="line">
                                    <tr>
                                        <td style="font-size: 10px;">
                                            <span t-if="line.product_id" t-field="line.product_id.name"/>
                                            <span t-if="not line.product_id" t-field="line.name"/>
                                        </td>
                                       
                                        <td class="text-right" style="font-size: 10px;">
                                            <span t-if="line.product_id and line.product_uom_qty" t-field="line.product_uom_qty"/>
                                        </td>
                                        <td class="text-center" style="font-size: 10px;">
                                            <span t-if="line.packaging_id" t-field="line.packaging_id.name"/>
                                            <span t-if="not line.packaging_id and line.product_uom" t-field="line.product_uom.name"/>
                                        </td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>

                        <!-- Sección de OBSERVACIONES -->
                        <div class="mb32">
                            <table class="table table-bordered" style="margin-bottom: 20px;">
                                <tr>
                                    <td style="background-color: rgb(233, 233, 233); text-align: center; font-weight: bold; padding: 8px;">
                                        OBSERVACIONES
                                    </td>
                                </tr>
                                <tr>
                                    <td style="min-height: 80px; padding: 10px; font-size: 11px; vertical-align: top;">
                                        <span t-if="doc.observaciones" t-field="doc.observaciones"/>
                                        <span t-if="not doc.observaciones" style="color: #ccc; font-style: italic;">
                                            Sin observaciones registradas
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- Sección de FIRMAS -->
                        <div style="margin-top: 40px;">
                            <table class="table table-bordered" style="width: 100%;">
                                <tr>
                                    <!-- Columna Firma del Cliente -->
                                    <td style="width: 50%; padding: 0; vertical-align: top;">
                                        <table style="width: 100%; height: 140px; border: none;">
                                            <tr>
                                                <td style="text-align: center; font-weight: bold; background-color: rgb(233, 233, 233); padding: 8px; border: 1px solid #000;">
                                                    FIRMA DEL CLIENTE
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="height: 100px; border: 1px solid #000; border-top: none; background-color: #fff;">
                                                    <!-- Espacio en blanco para firma -->
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <!-- Columna Firma del Chofer -->
                                    <td style="width: 50%; padding: 0; vertical-align: top;">
                                        <table style="width: 100%; height: 140px; border: none;">
                                            <tr>
                                                <td style="text-align: center; font-weight: bold; background-color: rgb(233, 233, 233); padding: 8px; border: 1px solid #000;">
                                                    FIRMA DEL CHOFER
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="height: 100px; border: 1px solid #000; border-top: none; background-color: #fff;">
                                                    <!-- Espacio en blanco para firma -->
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <div class="oe_structure"/>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```
```

-e ### ./security/ir.model.access.csv
```
id,name,model_id:id,perm_read,perm_write,perm_create,perm_unlink
access_service_order,access_service_order,model_service_order,1,1,1,1
access_service_order_line,access_service_order_line,model_service_order_line,1,1,1,1
```

-e ### ./security/security.xml
```
<odoo>
  <data noupdate="1">
    <record id="group_service_order_user" model="res.groups">
      <field name="name">Service Order User</field>
      <field name="category_id" ref="base.module_category_services"/>
    </record>
    <record id="group_service_order_manager" model="res.groups">
      <field name="name">Service Order Manager</field>
      <field name="category_id" ref="base.module_category_services"/>
      <field name="implied_ids" eval="[(4, ref('group_service_order_user'))]"/>
    </record>
  </data>
</odoo>
```

-e ### ./views/account_move_form_extension.xml
```
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <record id="account_invoice_lines_plan_manejo" model="ir.ui.view">
    <field name="name">account.move.form.invoice_lines.plan_manejo</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_move_form"/>
    <field name="arch" type="xml">
      <!-- Dentro de la pestaña Invoice Lines, después de product_id -->
      <xpath expr="//page[@id='invoice_tab']//list/field[@name='product_id']"
             position="after">
        <field name="plan_manejo"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/account_move_service_link_view.xml
```
<odoo>
  <record id="view_move_form_service_order_link" model="ir.ui.view">
    <field name="name">account.move.form.service_order.link</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_move_form"/>
    <field name="arch" type="xml">
      <!-- Después de invoice_origin mostramos nuestro campo -->
      <xpath expr="//group[@name='sale_info_group']/field[@name='invoice_origin']" position="after">
        <field name="service_order_id" readonly="1"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/product_template_view.xml
```
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <record id="view_product_template_form_residuos" model="ir.ui.view">
    <field name="name">product.template.form.residuos</field>
    <field name="model">product.template</field>
    <field name="inherit_id" ref="product.product_template_form_view"/>
    <field name="arch" type="xml">
      <notebook position="inside">
        <page string="Datos Ambientales" name="environmental_data">
          <group string="Clasificación del Residuo" col="2">
            <field name="clasificacion_residuo"/>
            <field name="envase_tipo_default"/>
            <field name="envase_capacidad_default"/>
          </group>
        </page>
      </notebook>
    </field>
  </record>
</odoo>
```

-e ### ./views/sale_order_inherit.xml
```
<odoo>
  <record id="view_sale_order_button_service" model="ir.ui.view">
    <field name="name">sale.order.form.service.buttons</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//header" position="inside">
        <!-- Botón para crear órdenes de servicio -->
        <button name="action_create_service_order"
                string="Crear Orden de Servicio"
                type="object"
                class="btn-secondary"
                groups="sales_team.group_sale_salesman"/>
        <!-- Botón para ver las órdenes de servicio creadas -->
        <button name="action_view_service_orders"
                string="Ver Órdenes de Servicio"
                type="object"
                class="btn-secondary"
                groups="sales_team.group_sale_salesman"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/service_order_invoice_button.xml
```
<odoo>
  <record id="view_service_order_form_invoice" model="ir.ui.view">
    <field name="name">service.order.form.invoice.button</field>
    <field name="model">service.order</field>
    <!-- Referencia ahora al form view, no a la acción -->
    <field name="inherit_id" ref="view_service_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//header" position="inside">
        <button name="action_create_invoice"
                string="Crear Factura"
                type="object"
                class="btn-success"
                invisible="state != 'done'"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/service_order_invoice_view_button.xml
```
<odoo>
  <record id="view_service_order_form_view_invoices" model="ir.ui.view">
    <field name="name">service.order.form.view_invoices.button</field>
    <field name="model">service.order</field>
    <field name="inherit_id" ref="view_service_order_form"/>
    <field name="arch" type="xml">
      <!-- Inserta el botón inmediatamente después de “Crear Factura” -->
      <xpath expr="//header/button[@name='action_create_invoice']" position="after">
        <button name="action_view_linked_invoices"
                string="Ver Facturas"
                type="object"
                class="btn-secondary"
                invisible="not invoice_count"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/service_order_print_button.xml
```
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <record id="view_service_order_form_print_button" model="ir.ui.view">
    <field name="name">service.order.form.print.button</field>
    <field name="model">service.order</field>
    <field name="inherit_id" ref="view_service_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//header/button[@name='action_cancel']" position="after">
        <!-- Botón para imprimir el reporte -->
        <button name="%(action_report_service_order)d"
                string="Imprimir"
                type="action"
                class="btn-secondary"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### ./views/service_order_views.xml
```
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <!-- Acción principal -->
  <record id="action_service_order" model="ir.actions.act_window">
    <field name="name">Órdenes de Servicio</field>
    <field name="res_model">service.order</field>
    <field name="view_mode">list,form</field>
  </record>

  <!-- MENÚ RAÍZ CON ÍCONO -->
  <record id="menu_service_order_root" model="ir.ui.menu">
    <field name="name">Servicios</field>
    <field name="sequence">10</field>
    <field name="action" ref="action_service_order"/>
    <field name="web_icon">service_order,static/description/icon.png</field>
  </record>

  <!-- Secuencia para generar automáticamente el campo name de service.order -->
  <record id="seq_service_order" model="ir.sequence">
    <field name="name">Service Order</field>
    <field name="code">service.order</field>
    <field name="prefix">SO-</field>
    <field name="padding">4</field>
    <field name="company_id" eval="False"/>
  </record>

  <!-- Lista de service.order -->
  <record id="view_service_order_list" model="ir.ui.view">
    <field name="name">service.order.list</field>
    <field name="model">service.order</field>
    <field name="type">list</field>
    <field name="arch" type="xml">
      <list string="Órdenes de Servicio">
        <field name="name"/>
        <field name="partner_id"/>
        <field name="date_order"/>
        <field name="state"/>
      </list>
    </field>
  </record>

  <!-- Formulario de service.order -->
  <record id="view_service_order_form" model="ir.ui.view">
    <field name="name">service.order.form</field>
    <field name="model">service.order</field>
    <field name="type">form</field>
    <field name="arch" type="xml">
      <form string="Orden de Servicio">
        <header>
          <button name="action_confirm"
                  string="Confirmar"
                  type="object"
                  class="btn-primary"
                  invisible="state != 'draft'"/>
          <button name="action_set_done"
                  string="Marcar Completado"
                  type="object"
                  invisible="state != 'confirmed'"/>
          <button name="action_cancel"
                  string="Cancelar"
                  type="object"
                  invisible="state not in ['draft','confirmed']"/>

          <field name="state"
                 widget="statusbar"
                 statusbar_visible="draft,confirmed,done,cancel"
                 statusbar_colors='{"draft":"blue","confirmed":"orange","done":"green","cancel":"red"}'/>
        </header>
        <sheet>
          <!-- Campos principales divididos en dos columnas -->
          <group col="2">
            <group>
              <field name="name"/>
              <field name="sale_order_id"/>
              <field name="partner_id"/>
              <field name="date_order"/>
            </group>
            <group>
              <field name="generador_id" string="Generador"/>
              <field name="contact_name" string="Nombre de contacto"/>
              <field name="contact_phone" string="Teléfono de contacto"/>
              <field name="transportista_id" string="Transportista"/>
              <field name="pickup_location" string="Ubicación de recolección"/>
            </group>
          </group>

          <!-- Segunda fila de campos adicionales -->
          <group col="2" class="mt16">
            <group>
              <field name="camion" string="Camión"/>
              <field name="numero_placa" string="Número de Placa"/>
              <field name="chofer_id" string="Chofer"/>
              <field name="transportista_responsable" string="Responsable Transportista"/>
            </group>
            <group>
              <field name="remolque1" string="Remolque 1"/>
              <field name="remolque2" string="Remolque 2"/>
              <field name="numero_bascula" string="Número de báscula"/>
              <field name="generador_responsable" string="Responsable Generador"/>
            </group>
          </group>

          <!-- Tercera fila para destinatario -->
          <group col="2" class="mt16">
            <group>
              <field name="destinatario_id" string="Destinatario Final"/>
            </group>
            <group>
              <!-- Espacio para más campos si es necesario -->
            </group>
          </group>

          <!-- Notebook con Líneas de Servicio y Observaciones -->
          <notebook>
            <page string="Líneas de Servicio">
              <field name="line_ids">
                <list editable="bottom">
                  <!-- Campo product_id invisible pero necesario para las condiciones -->
                  <field name="product_id" column_invisible="1"/>
                  <!-- Columna combinada: muestra producto o nota -->
                  <field name="description" string="Residuo / Equivalente"/>
                  <field name="residue_type"/>
                  <field name="plan_manejo"/> 
                  <field name="packaging_id" string="Embalaje"/>
                  <!-- Oculta cantidad y unidad cuando no hay producto -->
                  <field name="product_uom_qty" invisible="not product_id"/>
                  <field name="product_uom"     invisible="not product_id"/>
                  <!-- Campo computado para mostrar en reporte -->
                  <field name="display_uom" string="Unidad/Embalaje" readonly="1"/>
                </list>
              </field>
            </page>
            <page string="Observaciones">
              <group>
                <field name="observaciones" nolabel="1" placeholder="Ingrese observaciones adicionales..." widget="text"/>
              </group>
            </page>
          </notebook>

        </sheet>
      </form>
    </field>
  </record>
</odoo>
```

### __init__.py
```python
from . import models
```

### __manifest__.py
```python
{
    'name': 'Service Order',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio independiente',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/service_order_views.xml',                    # 1. Vistas base
        'reports/service_order_report.xml',                 # 2. Definición del reporte 
        'views/service_order_print_button.xml',             # 3. Botón que referencia el reporte
        'views/sale_order_inherit.xml',                     # 4. Resto de vistas
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
```

