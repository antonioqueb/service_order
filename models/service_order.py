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
        default=lambda self: _('New')
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        ondelete='set null'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True
    )
    
    date_order = fields.Datetime(
        string='Fecha',
        required=True,
        default=fields.Datetime.now
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Completado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)
    
    invoicing_status = fields.Selection([
        ('no', 'No Facturado'),
        ('invoiced', 'Facturado'),
    ], string='Estado de Facturación', default='no', readonly=True, tracking=True, copy=False)
    
    line_ids = fields.One2many(
        'service.order.line',
        'service_order_id',
        string='Líneas'
    )
    
    observaciones = fields.Text(string='Observaciones')
    
    service_frequency = fields.Selection([
        ('unico', 'Único'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ], string='Frecuencia del Servicio')
    
    residue_new = fields.Boolean(string='Residuo Nuevo')
    requiere_visita = fields.Boolean(string='Requiere Visita')
    pickup_location = fields.Char(string='Ubicación de Recolección')
    
    generador_id = fields.Many2one('res.partner', string='Generador')
    contact_name = fields.Char(string='Nombre de Contacto')
    contact_phone = fields.Char(string='Teléfono de Contacto')
    transportista_id = fields.Many2one('res.partner', string='Transportista')
    camion = fields.Char(string='Camión')
    numero_placa = fields.Char(string='Número de Placa')
    chofer_id = fields.Many2one('res.partner', string='Chofer')
    transportista_responsable = fields.Char(string='Responsable Transportista')
    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')
    numero_bascula = fields.Char(string='Número de Báscula')
    generador_responsable = fields.Char(string='Responsable Generador')
    destinatario_id = fields.Many2one('res.partner', string='Destinatario Final')
    
    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_count',
        store=False
    )
    
    invoice_ids = fields.One2many(
        'account.move',
        'service_order_id',
        string='Facturas',
        readonly=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('service.order') or _('New')
        return super(ServiceOrder, self).create(vals)
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_set_done(self):
        self.write({'state': 'done'})
    
    def action_cancel(self):
        self.write({'state': 'cancel'})
    
    @api.depends('invoice_ids', 'invoice_ids.state')
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