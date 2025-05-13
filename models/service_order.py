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
    camion_id = fields.Many2one(
        'fleet.vehicle', string='Camión'
    )
    chofer_id = fields.Many2one(
        'res.partner', string='Chofer'
    )
    remolque1_id = fields.Many2one(
        'fleet.vehicle', string='Remolque 1'
    )
    remolque2_id = fields.Many2one(
        'fleet.vehicle', string='Remolque 2'
    )
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