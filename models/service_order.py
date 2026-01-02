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

    # Frecuencia (mantener como estaba)
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
    # Campo legacy (no se elimina para no romper datos previos)
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

    # Legacy (se conserva) - ahora se PERSISTE de forma robusta al guardar
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

    # Legacy (no se elimina para no romper datos)
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
        """
        Busca el primer contacto relacionado al cliente (hijos o el mismo) que tenga la etiqueta.
        Si no existe, regresa False.
        """
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
        """Valida si candidate es client o un hijo directo de client."""
        if not candidate or not client:
            return False
        return candidate.id == client.id or candidate.parent_id.id == client.id

    def _get_contact_phone_safe(self, partner):
        """Obtiene teléfono robusto, sin tronar si `mobile` no existe."""
        if not partner:
            return False
        mobile = getattr(partner, 'mobile', False)
        return partner.phone or mobile or False

    def _prepare_contact_legacy_vals(self, partner):
        """Valores consistentes para legacy name/phone."""
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
        # Si el campo no existe en tu build, Odoo simplemente no lo toma como dependencia.
        # Aun así, el método usa getattr para leerlo de forma segura.
        'contact_partner_id.mobile',
    )
    def _compute_contact_legacy(self):
        """
        Mantiene compatibilidad:
        - Si hay contact_partner_id: siempre reflejar nombre/teléfono del contacto.
        - Si NO hay contact_partner_id: NO borrar valores legacy existentes.
        """
        for rec in self:
            if rec.contact_partner_id:
                vals = rec._prepare_contact_legacy_vals(rec.contact_partner_id)
                rec.contact_name = vals.get('contact_name')
                rec.contact_phone = vals.get('contact_phone')
            else:
                # No borrar históricos
                rec.contact_name = rec.contact_name or False
                rec.contact_phone = rec.contact_phone or False

    # -------------------------------------------------------------------------
    # ONCHANGES
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id_autofill(self):
        """
        - Autocompleta Generador por etiqueta "Generador" (si existe).
        - Limpia campos seleccionados si ya no pertenecen al cliente.
        """
        for rec in self:
            if not rec.partner_id:
                rec.generador_id = False
                rec.generador_responsable_id = False
                rec.contact_partner_id = False
                rec.pickup_location_id = False
                return

            # 1) Autocompletar generador por etiqueta
            gen = rec._find_related_contact_with_tag(rec.partner_id, 'Generador')
            rec.generador_id = gen.id if gen else False

            # 2) Limpiar responsable generador si no corresponde al cliente
            if rec.generador_responsable_id and not rec._is_partner_related_to_client(rec.generador_responsable_id, rec.partner_id):
                rec.generador_responsable_id = False

            # 3) Limpiar contacto si no corresponde al cliente
            if rec.contact_partner_id and not rec._is_partner_related_to_client(rec.contact_partner_id, rec.partner_id):
                rec.contact_partner_id = False

            # 4) Limpiar pickup si no corresponde al cliente
            if rec.pickup_location_id and not rec._is_partner_related_to_client(rec.pickup_location_id, rec.partner_id):
                rec.pickup_location_id = False

    @api.onchange('contact_partner_id')
    def _onchange_contact_partner_id(self):
        """
        UI: llena en pantalla y muestra warning amigable si el contacto no tiene teléfono.
        La persistencia se asegura en create/write y con compute store.
        """
        warning = False
        for rec in self:
            if rec.contact_partner_id:
                partner = rec.contact_partner_id
                phone = rec._get_contact_phone_safe(partner)

                # Forzar valores en el record (UX inmediata)
                rec.contact_name = partner.name or partner.display_name or False
                rec.contact_phone = phone

                if not phone:
                    warning = {
                        'title': _('Contacto sin teléfono'),
                        'message': _(
                            'El contacto seleccionado "%(contact)s" no tiene teléfono registrado.\n\n'
                            'Sugerencia:\n'
                            '• Abre el contacto y captura Teléfono (y/o Móvil), luego vuelve a seleccionarlo.'
                        ) % {'contact': partner.display_name}
                    }
            else:
                # No borramos legacy automáticamente
                pass

        if warning:
            return {'warning': warning}

    @api.onchange('transportista_id')
    def _onchange_transportista_id(self):
        """
        Si cambia transportista, y el responsable ya no pertenece, lo limpia.
        """
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
            # Secuencia
            if vals.get('name', _('New')) == _('New'):
                seq_date = vals.get('date_order') or fields.Datetime.now()
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'service.order',
                    sequence_date=seq_date,
                ) or _('New')

            # Autocompletar generador si no viene y hay partner_id
            if vals.get('partner_id') and not vals.get('generador_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                gen = self._find_related_contact_with_tag(partner, 'Generador')
                vals['generador_id'] = gen.id if gen else False

            # PERSISTENCIA ROBUSTA: si viene contact_partner_id, guardar legacy SIEMPRE
            if vals.get('contact_partner_id'):
                c = self.env['res.partner'].browse(vals['contact_partner_id'])
                if c:
                    vals.update(self._prepare_contact_legacy_vals(c))

        return super().create(vals_list)

    def write(self, vals):
        """
        PERSISTENCIA ROBUSTA:
        - Si cambia contact_partner_id (o se setea), recalcular y persistir contact_name/contact_phone.
        - Esto evita que el teléfono "se vea" en pantalla por onchange, pero se pierda al guardar.
        """
        if 'contact_partner_id' in vals:
            if vals.get('contact_partner_id'):
                partner = self.env['res.partner'].browse(vals['contact_partner_id'])
                if partner.exists():
                    vals.update(self._prepare_contact_legacy_vals(partner))
            else:
                # Si se limpia el contacto, NO borramos legacy automáticamente para no perder históricos
                vals.pop('contact_name', None)
                vals.pop('contact_phone', None)

        return super().write(vals)

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
