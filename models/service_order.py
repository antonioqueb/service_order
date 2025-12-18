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

    # CORRECCIÓN AQUÍ: Se agregan todas las opciones del CRM para evitar errores de validación
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
        # Mantenemos 'unico' por compatibilidad histórica si ya tenías registros
        ('unico', 'Único'), 
    ], string="Frecuencia del Servicio")

    residue_new = fields.Boolean(string='Residuo Nuevo')
    requiere_visita = fields.Boolean(string='Requiere Visita')
    pickup_location = fields.Char(string='Ubicación de Recolección')

    # =========================================================
    # ACTUALIZACIÓN: GENERADOR
    # =========================================================
    generador_id = fields.Many2one('res.partner', string='Generador')
    
    # Automatización: Si cambia el cliente, el generador es el mismo
    @api.onchange('partner_id')
    def _onchange_partner_id_set_generator(self):
        if self.partner_id:
            self.generador_id = self.partner_id

    contact_name = fields.Char(string='Nombre de Contacto')
    contact_phone = fields.Char(string='Teléfono de Contacto')

    # =========================================================
    # ACTUALIZACIÓN: TRANSPORTISTA
    # =========================================================
    # Default: Asigna la empresa actual (Company Partner)
    transportista_id = fields.Many2one(
        'res.partner', 
        string='Transportista',
        default=lambda self: self.env.company.partner_id
    )

    camion = fields.Char(string='Camión')
    numero_placa = fields.Char(string='Número de Placa')
    chofer_id = fields.Many2one('res.partner', string='Chofer')
    
    # =========================================================
    # ACTUALIZACIÓN: RESPONSABLES (Ahora son Contactos/Many2one)
    # =========================================================
    transportista_responsable_id = fields.Many2one(
        'res.partner', 
        string='Responsable Transportista',
        help="Contacto administrativo o logístico de la empresa transportista"
    )
    
    generador_responsable_id = fields.Many2one(
        'res.partner', 
        string='Responsable Generador',
        help="Contacto en sitio del generador"
    )

    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')
    numero_bascula = fields.Char(string='Número de Báscula')
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_date = vals.get('date_order') or fields.Datetime.now()
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'service.order',
                    sequence_date=seq_date,
                ) or _('New')
            
            # Lógica extra: si se crea sin generador, asignar el partner
            if vals.get('partner_id') and not vals.get('generador_id'):
                vals['generador_id'] = vals['partner_id']

        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_set_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

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