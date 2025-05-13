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
        'res.partner', string='Cliente', required=True
    )
    date_order = fields.Datetime(
        string='Fecha Pedido', default=fields.Datetime.now, required=True
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

    line_ids = fields.One2many(
        'service.order.line', 'service_order_id', string='Líneas de Servicio'
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

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_set_done(self):
        for rec in self:
            rec.state = 'done'
