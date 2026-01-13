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

    # =========================================================
    # INVOICING_STATUS CON ESTADOS GRANULARES
    # =========================================================
    invoicing_status = fields.Selection(
        [
            ('no', 'No Facturado'),
            ('draft', 'Factura Generada'),
            ('invoiced', 'Facturado'),
            ('paid', 'Pagado'),
        ],
        string='Estado de Facturación',
        compute='_compute_invoicing_status',
        store=True,
        tracking=True,
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
    # UBICACIÓN DE RECOLECCIÓN
    # =========================================================
    pickup_location_id = fields.Many2one(
        'res.partner',
        string='Ubicación de Recolección',
        ondelete='set null',
        tracking=True,
        help='Dirección/contacto seleccionado para la recolección.'
    )
    pickup_location = fields.Char(
        string='Ubicación de Recolección (texto)',
        help='Campo legacy.',
        tracking=False,
    )

    # =========================================================
    # GENERADOR
    # =========================================================
    generador_id = fields.Many2one(
        'res.partner',
        string='Generador',
        ondelete='set null',
        tracking=True,
    )

    generador_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Generador',
    )

    # =========================================================
    # CONTACTO
    # =========================================================
    contact_partner_id = fields.Many2one(
        'res.partner',
        string='Nombre de Contacto',
        ondelete='set null',
        tracking=True,
    )

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
    # TRANSPORTISTA Y LOGÍSTICA
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
    )

    remolque1 = fields.Char(string='Remolque 1')
    remolque2 = fields.Char(string='Remolque 2')

    bascula_1 = fields.Char(string='Báscula 1')
    bascula_2 = fields.Char(string='Báscula 2')
    numero_bascula = fields.Char(string='Número de Báscula (legacy)')

    destinatario_id = fields.Many2one('res.partner', string='Destinatario Final')

    # =========================================================
    # FACTURACIÓN (CORREGIDO: MANY2MANY REAL)
    # =========================================================
    
    # Definimos la relación inversa EXACTA a la que definimos en account.move
    # Esto permite que Odoo maneje la base de datos correctamente sin errores de "not stored".
    invoice_ids = fields.Many2many(
        'account.move',
        'account_move_service_order_rel', # Nombre tabla intermedia (DEBE coincidir con el de account.move)
        'service_order_id',               # Columna de este modelo
        'move_id',                        # Columna del otro modelo
        string='Facturas',
        readonly=True,
    )

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_count',
        store=False,
    )

    # =========================================================
    # CAMPOS FINANCIEROS
    # =========================================================
    amount_untaxed = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        compute='_compute_currency_id',
        store=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    def _get_all_linked_invoices(self):
        """
        Obtiene facturas reales (Many2many) + facturas legacy (origen).
        """
        self.ensure_one()
        
        # 1. Facturas vinculadas correctamente por el nuevo sistema Many2many
        invoices = self.invoice_ids
        
        # 2. Búsqueda Legacy: Por invoice_origin (si existen facturas viejas sin el vínculo relacional)
        if self.name:
            legacy_invoices = self.env['account.move'].search([
                ('invoice_origin', '=', self.name),
                ('move_type', '=', 'out_invoice'),
                ('id', 'not in', invoices.ids) # Evitar duplicados
            ])
            if legacy_invoices:
                invoices |= legacy_invoices
        
        return invoices

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.payment_state')
    def _compute_invoicing_status(self):
        """
        Estado de facturación. Ahora depende de 'invoice_ids' de forma segura
        porque invoice_ids es un campo almacenado (relacional).
        """
        for order in self:
            invoices = order._get_all_linked_invoices()
            
            # Filtrar solo las no canceladas
            active_invoices = invoices.filtered(lambda inv: inv.state != 'cancel')
            
            if not active_invoices:
                order.invoicing_status = 'no'
                continue
            
            # Verificar si hay alguna pagada
            paid_invoices = active_invoices.filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state in ('paid', 'in_payment', 'reversed')
            )
            if paid_invoices:
                order.invoicing_status = 'paid'
                continue
            
            # Verificar si hay alguna confirmada (posted)
            posted_invoices = active_invoices.filtered(lambda inv: inv.state == 'posted')
            if posted_invoices:
                order.invoicing_status = 'invoiced'
                continue
            
            # Verificar si hay alguna en borrador
            draft_invoices = active_invoices.filtered(lambda inv: inv.state == 'draft')
            if draft_invoices:
                order.invoicing_status = 'draft'
                continue
            
            # Default
            order.invoicing_status = 'no'

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            invoices = order._get_all_linked_invoices()
            order.invoice_count = len(invoices.filtered(lambda inv: inv.state != 'cancel'))

    @api.depends('sale_order_id', 'sale_order_id.currency_id')
    def _compute_currency_id(self):
        for order in self:
            if order.sale_order_id:
                order.currency_id = order.sale_order_id.currency_id
            else:
                order.currency_id = order.env.company.currency_id

    @api.depends('line_ids.price_unit', 'line_ids.product_uom_qty', 'line_ids.product_id')
    def _compute_amounts(self):
        for order in self:
            total = sum(
                line.price_unit * line.product_uom_qty
                for line in order.line_ids
                if line.product_id
            )
            order.amount_untaxed = total

    @api.depends(
        'contact_partner_id',
        'contact_partner_id.name',
        'contact_partner_id.display_name',
        'contact_partner_id.phone',
    )
    def _compute_contact_legacy(self):
        for rec in self:
            if rec.contact_partner_id:
                vals = rec._prepare_contact_legacy_vals(rec.contact_partner_id)
                rec.contact_name = vals.get('contact_name')
                rec.contact_phone = vals.get('contact_phone')
            else:
                rec.contact_name = rec.contact_name or False
                rec.contact_phone = rec.contact_phone or False

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
    
    def _has_blocking_invoices(self):
        self.ensure_one()
        invoices = self._get_all_linked_invoices()
        blocking = invoices.filtered(lambda inv: inv.state == 'posted')
        return bool(blocking)

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

            if vals.get('contact_partner_id'):
                c = self.env['res.partner'].browse(vals['contact_partner_id'])
                if c:
                    vals.update(self._prepare_contact_legacy_vals(c))

        return super().create(vals_list)

    def write(self, vals):
        if 'contact_partner_id' in vals:
            if vals.get('contact_partner_id'):
                partner = self.env['res.partner'].browse(vals['contact_partner_id'])
                if partner.exists():
                    vals.update(self._prepare_contact_legacy_vals(partner))
            else:
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
        for order in self:
            if order._has_blocking_invoices():
                raise UserError(_('No se puede cancelar una orden con facturas confirmadas. Cancele primero las facturas.'))
        self.write({'state': 'cancel'})

    def action_set_draft(self):
        """Restablecer a borrador desde cancelado, confirmado o done"""
        for order in self:
            if order.state not in ('cancel', 'confirmed', 'done'):
                raise UserError(_('Solo se pueden restablecer a borrador órdenes canceladas, confirmadas o completadas.'))
            # Solo bloquear si hay facturas confirmadas (posted), no borradores
            if order._has_blocking_invoices():
                raise UserError(_('No se puede restablecer a borrador una orden con facturas confirmadas. Cancele primero las facturas.'))
        self.write({'state': 'draft'})

    # -------------------------------------------------------------------------
    # INVOICES
    # -------------------------------------------------------------------------
    def action_view_linked_invoices(self):
        self.ensure_one()
        invoices = self._get_all_linked_invoices()

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
    
    # -------------------------------------------------------------------------
    # ACCIÓN PARA FORZAR RECÁLCULO
    # -------------------------------------------------------------------------
    def action_recompute_invoicing_status(self):
        """Fuerza el recálculo del estado de facturación"""
        self._compute_invoicing_status()
        return True