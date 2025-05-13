-e ### models/service_order_line.py
```
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
```

-e ### models/__init__.py
```
from . import service_order
from . import service_order_line
from . import sale_order_extension
```

-e ### models/sale_order_extension.py
```
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # Crea la orden de servicio "desde cero"
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            # cualquier otro campo por defecto que necesites…
        })
        return {
            'name': 'Orden de Servicio',
            'type': 'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id': service.id,
            'target': 'current',
        }
```

-e ### models/service_order.py
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

-e ### views/sale_order_inherit.xml
```
<odoo>
  <record id="view_sale_order_button_service" model="ir.ui.view">
    <field name="name">sale.order.form.service.button</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//header" position="inside">
        <button name="action_create_service_order"
                string="Crear Orden de Servicio"
                type="object"
                class="btn-secondary"
                groups="sales_team.group_sale_salesman"/>
      </xpath>
    </field>
  </record>
</odoo>
```

-e ### views/service_order_views.xml
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
    <field name="name">Órdenes de Servicio</field>
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
                  invisible="state not in ['draft', 'confirmed']"/>
          <!-- Statusbar -->
          <field name="state"
                 widget="statusbar"
                 statusbar_visible="draft,confirmed,done,cancel"
                 statusbar_colors='{"draft":"blue","confirmed":"orange","done":"green","cancel":"red"}'/>
        </header>
        <sheet>
          <group>
            <field name="name"/>
            <field name="sale_order_id"/>
            <field name="partner_id"/>
            <field name="date_order"/>
          </group>
          <notebook>
            <page string="Líneas de Servicio">
              <field name="line_ids">
                <list editable="bottom">
                  <field name="product_id"/>
                  <field name="residue_type"/>
                  <field name="packaging_id" string="Embalaje"/>
                  <field name="product_uom_qty"/>
                  <field name="product_uom"/>
                </list>
              </field>
            </page>
            <page string="Configuración CRM">
              <group>
                <field name="service_frequency"/>
                <field name="pickup_location"/>
                <field name="residue_new"/>
                <field name="requiere_visita"/>
              </group>
            </page>
            <page string="Transporte">
              <group>
                <field name="generador_id" string="Generador"/>
                <field name="contact_name" string="Nombre de contacto"/>
                <field name="contact_phone" string="Teléfono de contacto"/>
              </group>
              <group>
                <field name="transportista_id" string="Transportista"/>
                <field name="camion_id" string="Camión"/>
                <field name="chofer_id" string="Chofer"/>
              </group>
              <group>
                <field name="remolque1_id" string="Remolque 1"/>
                <field name="remolque2_id" string="Remolque 2"/>
                <field name="numero_bascula" string="Número de báscula"/>
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
```
from . import models
```
### __manifest__.py
```
{
    'name': 'Service Order',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Gestión de Órdenes de Servicio independiente',
    'author': 'Alphaqueb Consulting',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/service_order_views.xml',
        'views/sale_order_inherit.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
```
