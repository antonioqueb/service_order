## ./__init__.py
```py
# -*- coding: utf-8 -*-
from . import models```

## ./__manifest__.py
```py
{
    'name': 'Service Order',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio independiente',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'account'],
    'data': [
        'security/security.xml',                            # 0. Security groups first
        'security/ir.model.access.csv',    
        'data/service_order_sequence.xml',                 # 1. Access rights
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
}```

## ./data/service_order_sequence.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data noupdate="1">

    <record id="seq_service_order" model="ir.sequence">
      <field name="name">Service Order</field>
      <field name="code">service.order</field>

      <!-- Folio: SO/AAAAMMDD/0001 -->
      <field name="prefix">SO/%(year)s%(month)s%(day)s/</field>
      <field name="padding">4</field>

      <!-- Secuencia global (sin compañía) -->
      <field name="company_id" eval="False"/>
    </record>

  </data>
</odoo>
```

## ./models/__init__.py
```py
# -*- coding: utf-8 -*-
from . import service_order
from . import service_order_line
from . import service_order_invoice
from . import service_order_invoice_view
from . import account_move_service_link
from . import product_extension
from . import sale_order_extension```

## ./models/account_move_service_link.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio Origen',
        readonly=False,  # *** EDITABLE: Permite establecer y modificar el valor ***
        copy=False,
        help='Orden de Servicio origen de esta factura',
        tracking=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}  # Solo readonly cuando está posted o cancelada
    )
    
    def write(self, vals):
        # Prevenir cambio de orden de servicio en facturas no en borrador
        if 'service_order_id' in vals:
            for move in self:
                # Solo prevenir el cambio si la factura ya está confirmada Y se intenta cambiar a otra orden diferente
                if move.state in ('posted', 'cancel') and move.service_order_id and vals['service_order_id'] != move.service_order_id.id:
                    raise UserError(_('No se puede cambiar la orden de servicio de una factura confirmada o cancelada.'))
        
        # Ejecutar el write original
        res = super(AccountMove, self).write(vals)
        
        # CRÍTICO: Actualizar el estado de facturación cuando el estado cambia a 'posted'
        if 'state' in vals:
            for move in self:
                if move.service_order_id and move.move_type == 'out_invoice':
                    # Si la factura se confirma (posted), marcar orden como facturada
                    if move.state == 'posted':
                        move.service_order_id.sudo().write({'invoicing_status': 'invoiced'})
                    # Si la factura se cancela, verificar si revertir el estado
                    elif move.state == 'cancel':
                        # Buscar otras facturas no canceladas para esta orden
                        other_invoices = self.env['account.move'].search([
                            ('service_order_id', '=', move.service_order_id.id),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '=', 'posted'),
                            ('id', '!=', move.id)
                        ])
                        # Si no hay otras facturas válidas, marcar como no facturada
                        if not other_invoices:
                            move.service_order_id.sudo().write({'invoicing_status': 'no'})
        
        return res
    
    # Mantener también el override de _post por si acaso
    def _post(self, soft=True):
        """Sobrescribir _post como respaldo para marcar la orden como facturada"""
        res = super(AccountMove, self)._post(soft=soft)
        
        for move in self:
            if move.service_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                move.service_order_id.sudo().write({'invoicing_status': 'invoiced'})
        
        return res

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
            ('relleno_sanitario', 'Relleno Sanitario'),
        ],
        string="Plan de Manejo",
        help="Método de tratamiento y/o disposición final para el residuo según normatividad ambiental."
    )```

## ./models/product_extension.py
```py
# -*- coding: utf-8 -*-
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
    )```

## ./models/sale_order_extension.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()

        # Propagar ubicación recolección (nuevo selector si existe en sale)
        pickup_partner = getattr(self, 'pickup_location_id', False)
        pickup_location_id = pickup_partner.id if pickup_partner else False

        # Fallback legacy: si existiera un pickup_location tipo char en sale.order
        pickup_location_legacy = getattr(self, 'pickup_location', False)

        # Propagar destinatario final desde venta (si existe final_destination_id)
        final_dest = getattr(self, 'final_destination_id', False)
        destinatario_id = final_dest.id if final_dest else False

        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),

            # NUEVO: Ubicación select + legacy
            'pickup_location_id': pickup_location_id,
            'pickup_location': pickup_location_legacy,

            # NUEVO: Destinatario final propagado
            'destinatario_id': destinatario_id,
        })

        # 2) Copiar líneas (mantener funcionalidad existente)
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                weight_kg = 0.0
                capacity = ""

                # Obtener peso
                if hasattr(line, 'residue_weight_kg') and line.residue_weight_kg:
                    weight_kg = line.residue_weight_kg
                elif hasattr(self, 'opportunity_id') and self.opportunity_id:
                    residue = self.opportunity_id.residue_line_ids.filtered(
                        lambda r: r.product_id == line.product_id
                    )
                    if residue:
                        weight_kg = residue[0].weight_kg
                        capacity = residue[0].capacity if hasattr(residue[0], 'capacity') else 0.0

                # Obtener capacidad
                if hasattr(line, 'residue_capacity') and line.residue_capacity:
                    capacity = line.residue_capacity

                # UoM (Odoo 19)
                uom_id = line.product_uom_id.id if hasattr(line, 'product_uom_id') else False

                # Embalaje (custom en tu módulo de propagate)
                packaging_id_val = False
                if hasattr(line, 'residue_packaging_id') and line.residue_packaging_id:
                    packaging_id_val = line.residue_packaging_id.id

                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': uom_id,
                    'weight_kg': weight_kg,
                    'capacity': capacity,
                    'packaging_id': packaging_id_val,  # uom.uom
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
                    'price_unit': line.price_unit,  # mantiene precio pactado
                }
                self.env['service.order.line'].create(vals)

        # 3) Abrir la vista en modo formulario
        return {
            'name': 'Orden de Servicio',
            'type': 'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id': service.id,
            'target': 'current',
        }

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name': f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action
```

## ./models/service_order_invoice_view.py
```py
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

## ./models/service_order_invoice.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        """
        Método mejorado para crear facturas desde órdenes de servicio.
        - Valida que no existan facturas duplicadas
        - Copia líneas de producto Y líneas de notas
        - Establece automáticamente la relación service_order_id
        - Marca la orden como facturada
        """
        self.ensure_one()
        
        # ==========================================
        # VALIDACIONES PREVIAS
        # ==========================================
        
        # VALIDACIÓN 1: Verificar que no esté ya facturado
        if self.invoicing_status == 'invoiced':
            raise UserError(_('Esta orden de servicio ya ha sido facturada. No se pueden crear múltiples facturas para la misma orden.'))
        
        # VALIDACIÓN 2: Verificar que no existan facturas previas activas
        existing_invoices = self.env['account.move'].search([
            ('service_order_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel')
        ])
        
        if existing_invoices:
            raise UserError(_('Ya existe una factura para esta orden de servicio: %s') % existing_invoices[0].name)
        
        # VALIDACIÓN 3: Verificar que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError(_("No hay líneas de producto que facturar."))

        # ==========================================
        # PREPARAR VALORES DE LA FACTURA
        # ==========================================
        
        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,  # Mantener referencia al número de orden
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
            # *** CRÍTICO: Agregar el service_order_id directamente en la creación ***
            'service_order_id': self.id,
        }

        # ==========================================
        # RECORRER TODAS LAS LÍNEAS
        # ==========================================
        # Recorre TODAS las líneas en el orden original (productos Y notas)
        for line in self.line_ids:
            if line.product_id:
                # ========================================
                # LÍNEA DE PRODUCTO
                # ========================================
                
                # === MODIFICADO: USAR EL PRECIO PACTADO ===
                # Antes: price = line.product_id.lst_price or 0.0
                price = line.price_unit
                # ==========================================
                
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
                # ========================================
                # LÍNEA DE NOTA
                # ========================================
                # Línea de nota nativa en la factura (sin producto)
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         line.description or '',
                }))

        # ==========================================
        # CREAR LA FACTURA
        # ==========================================
        invoice = self.env['account.move'].create(invoice_vals)
        
        # ==========================================
        # DOBLE SEGURIDAD
        # ==========================================
        # Verificar y establecer nuevamente si no se guardó correctamente
        if not invoice.service_order_id:
            invoice.write({'service_order_id': self.id})
        
        # ==========================================
        # ACTUALIZAR ESTADO DE FACTURACIÓN
        # ==========================================
        # Marcar la orden como facturada inmediatamente
        self.write({'invoicing_status': 'invoiced'})
        
        # ==========================================
        # RETORNAR ACCIÓN PARA ABRIR LA FACTURA
        # ==========================================
        return {
            'name':      _('Factura de Servicio'),
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }```

## ./models/service_order_line.py
```py
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
                )```

## ./models/service_order.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Orden de Servicio'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Número',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Cotización',
        ondelete='set null',
        tracking=True,
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
    )

    date_order = fields.Datetime(
        string='Fecha',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('done', 'Completado'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
    )

    invoicing_status = fields.Selection(
        [
            ('no', 'No Facturado'),
            ('invoiced', 'Facturado'),
        ],
        string='Estado de Facturación',
        default='no',
        readonly=True,
        tracking=True,
        copy=False,
    )

    line_ids = fields.One2many(
        'service.order.line',
        'service_order_id',
        string='Líneas',
    )

    observaciones = fields.Text(string='Observaciones')

    service_frequency = fields.Selection([
        ('diaria', 'Diaria'),
        ('2_veces_semana', '2 veces por semana'),
        ('3_veces_semana', '3 veces por semana'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
        ('bimensual', 'Bimensual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
        ('bajo_demanda', 'Bajo demanda'),
        ('emergencia', 'Emergencia/Urgente'),
        ('una_sola_vez', 'Una sola vez'),
        ('estacional', 'Estacional'),
        ('irregular', 'Irregular'),
        ('unico', 'Único'),
    ], string="Frecuencia del Servicio")

    residue_new = fields.Boolean(string='Residuo Nuevo')
    requiere_visita = fields.Boolean(string='Requiere Visita')

    # =========================================================
    # UBICACIÓN DE RECOLECCIÓN (NUEVO SELECT) + LEGACY
    # =========================================================
    pickup_location_id = fields.Many2one(
        'res.partner',
        string='Ubicación de Recolección',
        ondelete='set null',
        tracking=True,
        help='Dirección/contacto seleccionado para la recolección (propagado desde la orden de venta).'
    )
    pickup_location = fields.Char(
        string='Ubicación de Recolección (texto)',
        help='Campo legacy. Se mantiene por compatibilidad con órdenes antiguas.',
        tracking=False,
    )

    # =========================================================
    # GENERADOR (AUTOFILL POR ETIQUETA "Generador")
    # =========================================================
    generador_id = fields.Many2one(
        'res.partner',
        string='Generador',
        ondelete='set null',
        tracking=True,
        help='Contacto relacionado al cliente con etiqueta "Generador".'
    )

    generador_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Generador',
        help="Contacto en sitio del generador (filtrado por contactos del cliente)."
    )

    # =========================================================
    # CONTACTO (SELECCIÓN POR CONTACTO DEL CLIENTE) + LEGACY
    # =========================================================
    contact_partner_id = fields.Many2one(
        'res.partner',
        string='Nombre de Contacto',
        ondelete='set null',
        tracking=True,
        help='Selecciona un contacto existente del cliente.'
    )

    # OJO: compute store SIN depender de mobile (porque no existe en tu build)
    contact_name = fields.Char(
        string='Nombre de Contacto (legacy)',
        compute='_compute_contact_legacy',
        store=True,
        readonly=False,
    )
    contact_phone = fields.Char(
        string='Teléfono de Contacto (legacy)',
        compute='_compute_contact_legacy',
        store=True,
        readonly=False,
    )

    # =========================================================
    # TRANSPORTISTA
    # =========================================================
    transportista_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        default=lambda self: self.env.company.partner_id
    )

    camion = fields.Char(string='Camión')
    numero_placa = fields.Char(string='Número de Placa')
    chofer_id = fields.Many2one('res.partner', string='Chofer')

    transportista_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Transportista',
        help="Contacto administrativo o logístico de la empresa transportista (filtrado por contactos del transportista)."
    )

    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')

    # =========================================================
    # BÁSCULAS (NUEVO) + LEGACY
    # =========================================================
    bascula_1 = fields.Char(string='Báscula 1')
    bascula_2 = fields.Char(string='Báscula 2')

    numero_bascula = fields.Char(
        string='Número de Báscula (legacy)',
        help='Campo legacy. Se mantiene por compatibilidad con órdenes antiguas.'
    )

    destinatario_id = fields.Many2one('res.partner', string='Destinatario Final')

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_count',
        store=False,
    )

    invoice_ids = fields.One2many(
        'account.move',
        'service_order_id',
        string='Facturas',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    def _get_partner_category_by_name(self, name):
        return self.env['res.partner.category'].sudo().search([('name', 'ilike', name)], limit=1)

    def _find_related_contact_with_tag(self, partner, tag_name):
        if not partner:
            return False
        tag = self._get_partner_category_by_name(tag_name)
        if not tag:
            return False

        domain = [
            ('category_id', 'in', [tag.id]),
            '|', ('parent_id', '=', partner.id), ('id', '=', partner.id)
        ]
        return self.env['res.partner'].sudo().search(domain, order='id asc', limit=1)

    def _is_partner_related_to_client(self, candidate, client):
        if not candidate or not client:
            return False
        return candidate.id == client.id or candidate.parent_id.id == client.id

    def _get_contact_phone_safe(self, partner):
        """Lee phone y, si existiera en algún entorno, mobile. En tu build mobile no existe, por eso getattr."""
        if not partner:
            return False
        mobile = getattr(partner, 'mobile', False)
        return partner.phone or mobile or False

    def _prepare_contact_legacy_vals(self, partner):
        if not partner:
            return {}
        return {
            'contact_name': partner.name or partner.display_name or False,
            'contact_phone': self._get_contact_phone_safe(partner),
        }

    # -------------------------------------------------------------------------
    # COMPUTES (STORE)
    # -------------------------------------------------------------------------
    @api.depends(
        'contact_partner_id',
        'contact_partner_id.name',
        'contact_partner_id.display_name',
        'contact_partner_id.phone',
    )
    def _compute_contact_legacy(self):
        """
        - Si hay contact_partner_id: reflejar nombre/teléfono.
        - Si NO hay contact_partner_id: NO borrar valores legacy existentes.
        """
        for rec in self:
            if rec.contact_partner_id:
                vals = rec._prepare_contact_legacy_vals(rec.contact_partner_id)
                rec.contact_name = vals.get('contact_name')
                rec.contact_phone = vals.get('contact_phone')
            else:
                rec.contact_name = rec.contact_name or False
                rec.contact_phone = rec.contact_phone or False

    # -------------------------------------------------------------------------
    # ONCHANGES
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id_autofill(self):
        for rec in self:
            if not rec.partner_id:
                rec.generador_id = False
                rec.generador_responsable_id = False
                rec.contact_partner_id = False
                rec.pickup_location_id = False
                return

            gen = rec._find_related_contact_with_tag(rec.partner_id, 'Generador')
            rec.generador_id = gen.id if gen else False

            if rec.generador_responsable_id and not rec._is_partner_related_to_client(rec.generador_responsable_id, rec.partner_id):
                rec.generador_responsable_id = False

            if rec.contact_partner_id and not rec._is_partner_related_to_client(rec.contact_partner_id, rec.partner_id):
                rec.contact_partner_id = False

            if rec.pickup_location_id and not rec._is_partner_related_to_client(rec.pickup_location_id, rec.partner_id):
                rec.pickup_location_id = False

    @api.onchange('contact_partner_id')
    def _onchange_contact_partner_id(self):
        """
        UX: muestra warning si no hay teléfono. La persistencia la garantiza create/write y compute store.
        """
        warning = False
        for rec in self:
            if rec.contact_partner_id:
                partner = rec.contact_partner_id
                phone = rec._get_contact_phone_safe(partner)

                rec.contact_name = partner.name or partner.display_name or False
                rec.contact_phone = phone

                if not phone:
                    warning = {
                        'title': _('Contacto sin teléfono'),
                        'message': _(
                            'El contacto seleccionado "%(contact)s" no tiene teléfono registrado.\n\n'
                            'Sugerencia:\n'
                            '• Abre el contacto y captura Teléfono, luego vuelve a seleccionarlo.'
                        ) % {'contact': partner.display_name}
                    }

        if warning:
            return {'warning': warning}

    @api.onchange('transportista_id')
    def _onchange_transportista_id(self):
        for rec in self:
            if rec.transportista_responsable_id and rec.transportista_id:
                ok = (rec.transportista_responsable_id.id == rec.transportista_id.id or
                      rec.transportista_responsable_id.parent_id.id == rec.transportista_id.id)
                if not ok:
                    rec.transportista_responsable_id = False

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_date = vals.get('date_order') or fields.Datetime.now()
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'service.order',
                    sequence_date=seq_date,
                ) or _('New')

            if vals.get('partner_id') and not vals.get('generador_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                gen = self._find_related_contact_with_tag(partner, 'Generador')
                vals['generador_id'] = gen.id if gen else False

            # Persistencia SIEMPRE
            if vals.get('contact_partner_id'):
                c = self.env['res.partner'].browse(vals['contact_partner_id'])
                if c:
                    vals.update(self._prepare_contact_legacy_vals(c))

        return super().create(vals_list)

    def write(self, vals):
        # Persistencia robusta al guardar
        if 'contact_partner_id' in vals:
            if vals.get('contact_partner_id'):
                partner = self.env['res.partner'].browse(vals['contact_partner_id'])
                if partner.exists():
                    vals.update(self._prepare_contact_legacy_vals(partner))
            else:
                # No borrar legacy automáticamente
                vals.pop('contact_name', None)
                vals.pop('contact_phone', None)

        return super().write(vals)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_set_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    # -------------------------------------------------------------------------
    # INVOICES
    # -------------------------------------------------------------------------
    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.move_type')
    def _compute_invoice_count(self):
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
            )
            order.invoice_count = len(invoices)

    def action_view_linked_invoices(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')

        if not invoices:
            raise UserError(_('No hay facturas vinculadas a esta orden de servicio.'))

        return {
            'name': _('Facturas Vinculadas'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False},
        }
```

## ./reports/__init__.py
```py
from . import service_order_report
```

## ./reports/service_order_report.xml
```xml
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
        <field name="paperformat_id" ref="base.paperformat_us"/>
    </record>

    <!-- Template del reporte -->
    <template id="service_order_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <style>
                            .formal-table {
                                width: 100%;
                                border-collapse: collapse;
                                font-size: 10px;
                                margin-bottom: 15px;
                                color: #000;
                            }
                            .formal-table th, .formal-table td {
                                border: 1px solid #000;
                                padding: 4px 6px;
                                vertical-align: middle;
                            }
                            .bg-header {
                                background-color: #f0f0f0;
                                font-weight: bold;
                                text-transform: uppercase;
                                width: 15%;
                            }
                            .section-title {
                                background-color: #333;
                                color: #fff;
                                padding: 3px 10px;
                                font-size: 11px;
                                font-weight: bold;
                                text-transform: uppercase;
                                margin-bottom: 0;
                            }
                            .text-right { text-align: right; }
                            .text-center { text-align: center; }
                        </style>

                        <div class="oe_structure"/>

                        <!-- Encabezado -->
                        <div class="row mb16 align-items-center">
                            <div class="col-8">
                                <h4 class="m-0" style="font-weight: bold; text-transform: uppercase;">Orden de Servicio</h4>
                            </div>
                            <div class="col-4 text-right">
                                <div style="border: 2px solid #000; padding: 5px; text-align: center;">
                                    <strong style="font-size: 14px;">FOLIO: <span t-field="doc.name"/></strong>
                                </div>
                            </div>
                        </div>

                        <!-- 1. INFORMACIÓN GENERAL -->
                        <div class="section-title">Información General y Logística</div>
                        <table class="formal-table">
                            <tr>
                                <td class="bg-header">Cliente</td>
                                <td style="width: 35%;"><span t-field="doc.partner_id.name"/></td>
                                <td class="bg-header">Fecha Servicio</td>
                                <td style="width: 35%;"><span t-field="doc.date_order" t-options='{"widget": "date"}'/></td>
                            </tr>
                            <tr>
                                <td class="bg-header">Dirección</td>
                                <td>
                                    <span t-field="doc.partner_id"
                                          t-options='{"widget": "contact", "fields": ["address"], "no_marker": True}'/>
                                </td>
                                <td class="bg-header">Cotización Ref.</td>
                                <td><span t-field="doc.sale_order_id.name"/></td>
                            </tr>
                            <tr>
                                <td class="bg-header">Contacto</td>
                                <td>
                                    <t t-if="doc.contact_partner_id">
                                        <span t-field="doc.contact_partner_id.name"/>
                                        <t t-if="doc.contact_partner_id.phone or doc.contact_partner_id.mobile">
                                            (<span t-esc="doc.contact_partner_id.phone or doc.contact_partner_id.mobile"/>)
                                        </t>
                                    </t>
                                    <t t-else="">
                                        <span t-field="doc.contact_name"/>
                                        <t t-if="doc.contact_phone"> (<span t-field="doc.contact_phone"/>)</t>
                                    </t>
                                </td>
                                <td class="bg-header">Estado Orden</td>
                                <td><span t-field="doc.state"/></td>
                            </tr>
                        </table>

                        <!-- 2. DETALLES DE TRANSPORTE -->
                        <div class="section-title">Detalles de Transporte y Carga</div>
                        <table class="formal-table">
                            <tr>
                                <td class="bg-header">Transportista</td>
                                <td style="width: 35%;"><span t-field="doc.transportista_id.name"/></td>
                                <td class="bg-header">Ubicación (Pickup)</td>
                                <td style="width: 35%;">
                                    <t t-if="doc.pickup_location_id">
                                        <span t-esc="((doc.pickup_location_id._display_address() or doc.pickup_location_id.name or '').replace('\n', ', '))"/>
                                    </t>
                                    <t t-else="">
                                        <span t-field="doc.pickup_location"/>
                                    </t>
                                </td>
                            </tr>
                            <tr>
                                <td class="bg-header">Resp. Transportista</td>
                                <td><span t-field="doc.transportista_responsable_id.name"/></td>
                                <td class="bg-header">Generador</td>
                                <td><span t-field="doc.generador_id.name"/></td>
                            </tr>
                            <tr>
                                <td class="bg-header">Chofer</td>
                                <td><span t-field="doc.chofer_id.name"/></td>
                                <td class="bg-header">Resp. Generador</td>
                                <td><span t-field="doc.generador_responsable_id.name"/></td>
                            </tr>

                            <!-- Básculas -->
                            <tr>
                                <td class="bg-header">Báscula 1</td>
                                <td>
                                    <t t-if="doc.bascula_1"><span t-field="doc.bascula_1"/></t>
                                    <t t-elif="doc.numero_bascula"><span t-field="doc.numero_bascula"/></t>
                                    <t t-else=""><span style="color:#ccc;">N/A</span></t>
                                </td>
                                <td class="bg-header">Báscula 2</td>
                                <td>
                                    <t t-if="doc.bascula_2"><span t-field="doc.bascula_2"/></t>
                                    <t t-else=""><span style="color:#ccc;">N/A</span></t>
                                </td>
                            </tr>

                            <tr>
                                <td class="bg-header">Remolque 1</td>
                                <td><span t-field="doc.remolque1"/></td>
                                <td class="bg-header">Remolque 2</td>
                                <td><span t-field="doc.remolque2"/></td>
                            </tr>
                        </table>

                        <!-- 3. DETALLE DE SERVICIOS -->
                        <div class="section-title">Detalle de Servicios</div>
                        <table class="formal-table">
                            <thead>
                                <tr style="background-color: #f0f0f0;">
                                    <th style="width: 30%; text-align: left;">Descripción / Producto</th>
                                    <th style="width: 15%; text-align: center;">Capacidad</th>
                                    <th style="width: 15%; text-align: center;">Peso (Kg)</th>
                                    <th style="width: 15%; text-align: center;">Cantidad</th>
                                    <th style="width: 25%; text-align: right;">Precio Unitario</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="doc.line_ids" t-as="line">
                                    <tr>
                                        <td>
                                            <strong t-if="line.product_id" t-field="line.product_id.name"/>
                                            <span t-if="not line.product_id" t-field="line.name"/>
                                            <div t-if="line.product_id and line.name != line.product_id.name" style="font-size: 9px; color: #555; font-style: italic;">
                                                <span t-field="line.name"/>
                                            </div>
                                        </td>
                                        <td class="text-center">
                                            <span t-if="line.capacity" t-field="line.capacity"/>
                                            <span t-else="">-</span>
                                        </td>
                                        <td class="text-center">
                                            <span t-if="line.weight_kg"><span t-field="line.weight_kg"/> kg</span>
                                            <span t-else="">-</span>
                                        </td>
                                        <td class="text-center">
                                            <span t-field="line.product_uom_qty"/>
                                            <span t-if="line.packaging_id" style="font-size: 9px;"> (<span t-field="line.packaging_id.name"/>)</span>
                                            <span t-elif="line.product_uom" style="font-size: 9px;"> <span t-field="line.product_uom.name"/></span>
                                        </td>
                                        <td class="text-right">
                                            <span t-if="line.product_id"
                                                  t-field="line.price_unit"
                                                  t-options='{"widget": "monetary", "display_currency": doc.sale_order_id.currency_id or doc.env.company.currency_id}'/>
                                        </td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>

                        <!-- 4. OBSERVACIONES Y FIRMAS -->
                        <div class="row mt16">
                            <div class="col-7">
                                <div class="section-title">Observaciones</div>
                                <div style="border: 1px solid #000; min-height: 105px; padding: 5px; font-size: 10px; background-color: #fff;">
                                    <span t-if="doc.observaciones" t-field="doc.observaciones"/>
                                    <span t-if="not doc.observaciones" style="color: #ccc; font-style: italic;">Sin observaciones adicionales.</span>
                                </div>
                            </div>

                            <div class="col-5">
                                <div class="section-title text-center">Autorización</div>
                                <div style="border: 1px solid #000; padding: 0;">
                                    <div style="height: 60px; border-bottom: 1px dotted #ccc;"></div>
                                    <div style="text-align: center; font-size: 9px; font-weight: bold; background-color: #f0f0f0; border-bottom: 1px solid #000;">
                                        FIRMA DE CONFORMIDAD (CLIENTE)
                                    </div>
                                    <div style="height: 60px; border-bottom: 1px dotted #ccc;"></div>
                                    <div style="text-align: center; font-size: 9px; font-weight: bold; background-color: #f0f0f0;">
                                        FIRMA DEL OPERADOR
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="row mt16">
                            <div class="col-12 text-center" style="font-size: 8px; color: #666;">
                                Este documento es un comprobante de servicio interno y no reemplaza a la factura fiscal.
                            </div>
                        </div>

                        <div class="oe_structure"/>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

## ./security/security.xml
```xml
<odoo>
  <data noupdate="1">
    <!-- Grupo Usuario -->
    <record id="group_service_order_user" model="res.groups">
      <field name="name">Service Order User</field>
      <!-- En Odoo 19, category_id ya no es un campo válido en res.groups en este contexto -->
    </record>

    <!-- Grupo Manager -->
    <record id="group_service_order_manager" model="res.groups">
      <field name="name">Service Order Manager</field>
      <!-- Se elimina category_id aquí también -->
      <field name="implied_ids" eval="[(4, ref('group_service_order_user'))]"/>
    </record>
  </data>
</odoo>```

## ./views/account_move_form_extension.xml
```xml
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
</odoo>```

## ./views/account_move_service_link_view.xml
```xml
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

## ./views/product_template_view.xml
```xml
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
</odoo>```

## ./views/sale_order_inherit.xml
```xml
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

## ./views/service_order_invoice_button.xml
```xml
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

## ./views/service_order_invoice_view_button.xml
```xml
<odoo>
  <record id="view_service_order_form_invoice" model="ir.ui.view">
    <field name="name">service.order.form.invoice.button</field>
    <field name="model">service.order</field>
    <!-- Referencia ahora al form view, no a la acción -->
    <field name="inherit_id" ref="view_service_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//header" position="inside">
        <!-- MODIFICADO: Ocultar botón si ya está facturado -->
        <button name="action_create_invoice"
                string="Crear Factura"
                type="object"
                class="btn-success"
                invisible="state != 'done' or invoicing_status == 'invoiced'"/>
      </xpath>
    </field>
  </record>
</odoo>```

## ./views/service_order_print_button.xml
```xml
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
</odoo>```

## ./views/service_order_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>

  <!-- =========================================================
       ACCIÓN PRINCIPAL
       ========================================================= -->
  <record id="action_service_order" model="ir.actions.act_window">
    <field name="name">Órdenes de Servicio</field>
    <field name="res_model">service.order</field>
    <field name="view_mode">list,form</field>
  </record>

  <!-- =========================================================
       MENÚ RAÍZ
       ========================================================= -->
  <record id="menu_service_order_root" model="ir.ui.menu">
    <field name="name">Servicios</field>
    <field name="sequence">10</field>
    <field name="action" ref="action_service_order"/>
    <field name="web_icon">service_order,static/description/icon.png</field>
  </record>

  <!-- =========================================================
       VISTA LISTA
       ========================================================= -->
  <record id="view_service_order_list" model="ir.ui.view">
    <field name="name">service.order.list</field>
    <field name="model">service.order</field>
    <field name="type">list</field>
    <field name="arch" type="xml">
      <list string="Órdenes de Servicio" default_order="date_order desc">
        <field name="name" string="Folio" class="fw-bold"/>
        <field name="date_order" string="Fecha"/>
        <field name="partner_id" string="Cliente"/>
        <field name="sale_order_id" string="Cotización" readonly="1"/>
        <field name="state" widget="badge"
               decoration-info="state == 'draft'"
               decoration-warning="state == 'confirmed'"
               decoration-success="state == 'done'"
               decoration-danger="state == 'cancel'"/>
        <field name="invoicing_status" string="Facturación" widget="badge"
               decoration-success="invoicing_status == 'invoiced'"
               decoration-info="invoicing_status == 'no'"/>
      </list>
    </field>
  </record>

  <!-- =========================================================
       VISTA FORMULARIO
       ========================================================= -->
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
                  class="btn-secondary"
                  invisible="state != 'confirmed'"/>

          <button name="action_cancel"
                  string="Cancelar"
                  type="object"
                  class="btn-secondary"
                  invisible="state not in ['draft','confirmed']"/>

          <field name="state"
                 widget="statusbar"
                 statusbar_visible="draft,confirmed,done,cancel"/>
        </header>

        <sheet>
          <widget name="web_ribbon" title="Borrador" bg_color="text-bg-info" invisible="state != 'draft'"/>
          <widget name="web_ribbon" title="Confirmada" bg_color="text-bg-warning" invisible="state != 'confirmed'"/>
          <widget name="web_ribbon" title="Completada" bg_color="text-bg-success" invisible="state != 'done'"/>
          <widget name="web_ribbon" title="Cancelada" bg_color="text-bg-danger" invisible="state != 'cancel'"/>
          <widget name="web_ribbon" title="Facturado" bg_color="text-bg-success" invisible="invoicing_status != 'invoiced'"/>

          <div class="oe_button_box" name="button_box">
            <button name="action_view_linked_invoices"
                    type="object"
                    class="oe_stat_button"
                    icon="fa-file-text-o"
                    invisible="invoice_count == 0">
              <field name="invoice_count" widget="statinfo" string="Facturas"/>
            </button>
          </div>

          <div class="oe_title">
            <h1>
              <field name="name" class="o_inline"/>
            </h1>
            <div class="text-muted">
              <span>Orden de servicio vinculada a </span>
              <field name="sale_order_id"
                     class="o_inline"
                     placeholder="Sin cotización"
                     readonly="1"
                     options="{'no_create': True}"/>
            </div>
          </div>

          <notebook>
            <page string="Resumen" name="page_summary">
              <group>
                <group string="Cliente y Referencias">

                  <!-- Cliente inmutable cuando proviene de cotización -->
                  <field name="partner_id"
                         options="{'no_create': True}"
                         readonly="sale_order_id"/>

                  <!--
                    Generador:
                    - SOLO contactos relacionados al cliente principal (parent_id = partner_id o el mismo partner)
                    - Y además con etiqueta/categoría "Generador"
                  -->
                  <field name="generador_id"
                         options="{'no_create': True}"
                         domain="[
                           '&amp;',
                             '|', ('parent_id', '=', partner_id), ('id', '=', partner_id),
                             ('category_id.name', 'ilike', 'Generador')
                         ]"
                         placeholder="(Sin contacto con etiqueta Generador)"/>

                  <!-- Responsable Generador: SOLO contactos relacionados al cliente -->
                  <field name="generador_responsable_id"
                         options="{'no_create': True}"
                         domain="['|', ('parent_id', '=', partner_id), ('id', '=', partner_id)]"
                         placeholder="Seleccionar contacto del cliente..."/>

                  <!-- Destinatario final: propagado desde venta; solo etiqueta Destino Final -->
                  <field name="destinatario_id"
                         options="{'no_create': True}"
                         domain="[('category_id.name', 'ilike', 'Destino Final')]"
                         placeholder="Seleccionar destinatario final..."/>

                  <field name="sale_order_id" string="Cotización" readonly="1" options="{'no_create': True}"/>
                  <field name="date_order"/>

                </group>

                <group string="Contacto y Recolección">

                  <!-- Nombre de contacto: select SOLO contactos del cliente -->
                  <field name="contact_partner_id"
                         options="{'no_create': True}"
                         domain="['|', ('parent_id', '=', partner_id), ('id', '=', partner_id)]"
                         placeholder="Seleccionar contacto del cliente..."/>

                  <!-- Teléfono: legacy (se llena desde el contacto), solo lectura para evitar captura manual -->
                  <field name="contact_phone" readonly="1"
                         placeholder="Se toma del contacto seleccionado"/>

                  <!-- Ubicación de recolección: select propagado desde venta; SOLO contactos del cliente -->
                  <field name="pickup_location_id"
                         options="{'no_create': True}"
                         domain="['|', ('parent_id', '=', partner_id), ('id', '=', partner_id)]"
                         placeholder="Seleccionar ubicación de recolección..."/>

                  <!-- Legacy pickup text oculto por defecto (compatibilidad) -->
                  <field name="pickup_location" invisible="1"/>

                  <field name="transportista_id" string="Transportista" options="{'no_create': True}"/>

                  <!-- Responsable Transportista: SOLO contactos del transportista -->
                  <field name="transportista_responsable_id"
                         options="{'no_create': True}"
                         domain="['|', ('parent_id', '=', transportista_id), ('id', '=', transportista_id)]"
                         placeholder="Seleccionar contacto del transportista..."/>

                </group>
              </group>
            </page>

            <page string="Logística" name="page_logistics">
              <group>
                <group string="Unidad y Operador">
                  <field name="camion" string="Camión"/>
                  <field name="numero_placa" string="Placas"/>
                  <field name="chofer_id" string="Chofer" options="{'no_create': True}"/>
                </group>

                <group string="Remolques y Básculas">
                  <field name="remolque1" string="Remolque 1"/>
                  <field name="remolque2" string="Remolque 2"/>

                  <!-- NUEVO -->
                  <field name="bascula_1" string="Báscula 1"/>
                  <field name="bascula_2" string="Báscula 2"/>

                  <!-- Legacy oculto -->
                  <field name="numero_bascula" invisible="1"/>
                </group>
              </group>
            </page>

            <page string="Líneas de Servicio" name="page_lines">
              <field name="line_ids">
                <list editable="bottom">
                  <field name="product_id" string="Producto/Servicio" options="{'no_create': True}"/>
                  <field name="currency_id" column_invisible="1"/>

                  <field name="description" string="Residuo / Equivalente"/>
                  <field name="residue_type" string="Tipo"/>
                  <field name="plan_manejo" string="Plan de Manejo"/>
                  <field name="packaging_id" string="Embalaje"/>

                  <field name="price_unit"
                         string="Precio Unitario"
                         widget="monetary"
                         options="{'currency_field': 'currency_id'}"
                         invisible="not product_id"/>

                  <field name="capacity" string="Capacidad" invisible="not product_id"/>
                  <field name="weight_kg" string="Peso (kg)" invisible="not product_id"/>
                  <field name="product_uom_qty" string="Cantidad" invisible="not product_id"/>
                  <field name="product_uom" string="UoM" invisible="not product_id"/>
                </list>
              </field>
            </page>

            <page string="Observaciones" name="page_notes">
              <group string="Notas">
                <field name="observaciones"
                       nolabel="1"
                       placeholder="Ingrese observaciones adicionales..."
                       widget="text"/>
              </group>
            </page>

          </notebook>

        </sheet>
      </form>
    </field>
  </record>

</odoo>
```

