# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT = {
    'service_order_child_only_display': True,
}

TRANSPORTISTA_TAG_NAME = 'Transportista'
DEFAULT_TRANSPORTISTA_NAME = 'SA Transporte'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends(
        'name',
        'complete_name',
        'parent_id',
        'parent_id.name',
        'email',
        'vat',
        'state_id',
        'country_id',
        'commercial_company_name',
    )
    @api.depends_context(
        'lang',
        'show_address',
        'show_address_only',
        'show_email',
        'show_vat',
        'service_order_child_only_display',
    )
    def _compute_display_name(self):
        """
        Ajuste contextual para Orden de Servicio.

        Problema:
        Odoo muestra contactos hijos como:
        "CLIENTE PADRE, CONTACTO HIJO"

        Requerimiento:
        En campos de Orden de Servicio donde el contacto ya está filtrado
        por un padre seleccionado, mostrar solo el nombre del contacto hijo.

        Este cambio NO afecta globalmente contactos, ventas, facturación, etc.
        Solo se activa cuando el campo Many2one envía el contexto:
        service_order_child_only_display=True
        """
        super()._compute_display_name()

        if not self.env.context.get('service_order_child_only_display'):
            return

        for partner in self:
            if partner.parent_id and partner.name:
                partner.display_name = partner.name

    def name_get(self):
        """
        Compatibilidad con flujos que todavía usen name_get para Many2one.

        En contexto normal conserva el comportamiento estándar.
        En contexto de Orden de Servicio muestra solo el nombre del hijo.
        """
        if not self.env.context.get('service_order_child_only_display'):
            return super().name_get()

        result = []
        for partner in self:
            if partner.parent_id and partner.name:
                name = partner.name
            else:
                name = partner.name or partner.complete_name or ''
            result.append((partner.id, name))
        return result


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

    # =========================================================
    # DIMENSIONES PARA REPORTES
    # =========================================================
    user_id = fields.Many2one(
        'res.users',
        string='Comercial',
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        help="Usuario responsable de la venta/servicio."
    )

    partner_city = fields.Char(
        related='partner_id.city',
        store=True,
        string="Ciudad Cliente"
    )

    partner_state_id = fields.Many2one(
        related='partner_id.state_id',
        store=True,
        string="Estado Cliente"
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

    observaciones = fields.Text(
        string='Observaciones',
        tracking=True,
    )

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
    ], string="Frecuencia del Servicio", tracking=True)

    residue_new = fields.Boolean(string='Residuo Nuevo', tracking=True)
    requiere_visita = fields.Boolean(string='Requiere Visita', tracking=True)

    # =========================================================
    # UBICACIÓN DE RECOLECCIÓN
    # =========================================================
    pickup_location_id = fields.Many2one(
        'res.partner',
        string='Ubicación de Recolección',
        ondelete='set null',
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
        help='Dirección/contacto seleccionado para la recolección.'
    )

    pickup_location = fields.Char(
        string='Ubicación de Recolección (texto)',
        help='Campo legacy.',
        tracking=True,
    )

    # =========================================================
    # GENERADOR
    # =========================================================
    generador_id = fields.Many2one(
        'res.partner',
        string='Generador',
        ondelete='set null',
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
    )

    generador_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Generador',
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
    )

    # =========================================================
    # CONTACTO
    # =========================================================
    contact_partner_id = fields.Many2one(
        'res.partner',
        string='Nombre de Contacto',
        ondelete='set null',
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
    )

    contact_name = fields.Char(
        string='Nombre de Contacto (legacy)',
        compute='_compute_contact_legacy',
        store=True,
        readonly=False,
        tracking=True,
    )

    contact_phone = fields.Char(
        string='Teléfono de Contacto (legacy)',
        compute='_compute_contact_legacy',
        store=True,
        readonly=False,
        tracking=True,
    )

    # =========================================================
    # TRANSPORTISTA Y LOGÍSTICA
    # =========================================================
    transportista_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        default=lambda self: self._get_default_transportista_id(),
        domain="[('category_id.name', 'ilike', 'Transportista')]",
        tracking=True,
        help='Transportista de la orden de servicio. Solo se muestran contactos con la etiqueta Transportista.',
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        tracking=True,
        help='Unidad de transporte principal.',
    )

    numero_placa = fields.Char(
        string='Número de Placa',
        tracking=True,
        help='Se rellena automáticamente desde el vehículo seleccionado.',
    )

    transportista_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Transportista',
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
    )

    chofer_id = fields.Many2one(
        'res.partner',
        string='Chofer',
        compute='_compute_chofer_id',
        inverse='_inverse_chofer_id',
        store=True,
        readonly=False,
        tracking=True,
        context=SERVICE_ORDER_CHILD_ONLY_DISPLAY_CONTEXT,
        help='Chofer asignado. Siempre coincide con el Responsable Transportista.',
    )

    remolque1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        tracking=True,
        domain="[('tag_ids.name', 'ilike', 'remolque')]",
        help='Seleccione el remolque 1 desde el catálogo de flota.',
    )

    remolque2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        tracking=True,
        domain="[('tag_ids.name', 'ilike', 'remolque')]",
        help='Seleccione el remolque 2 desde el catálogo de flota.',
    )

    remolque1 = fields.Char(
        string='Remolque 1 (placa/nombre)',
        compute='_compute_remolques_legacy',
        store=True,
        readonly=True,
    )

    remolque2 = fields.Char(
        string='Remolque 2 (placa/nombre)',
        compute='_compute_remolques_legacy',
        store=True,
        readonly=True,
    )

    bascula_1_numero = fields.Char(string='Número Báscula 1', tracking=True)
    bascula_1_peso = fields.Float(string='Peso Báscula 1 (kg)', tracking=True)
    bascula_2_numero = fields.Char(string='Número Báscula 2', tracking=True)
    bascula_2_peso = fields.Float(string='Peso Báscula 2 (kg)', tracking=True)
    numero_bascula = fields.Char(string='Número de Báscula (legacy)', tracking=True)

    destinatario_id = fields.Many2one(
        'res.partner',
        string='Destinatario Final',
        tracking=True,
    )

    # =========================================================
    # FACTURACIÓN
    # =========================================================
    invoice_ids = fields.Many2many(
        'account.move',
        'account_move_service_order_rel',
        'service_order_id',
        'move_id',
        string='Facturas',
        readonly=True,
    )

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_count',
        store=False,
    )

    transito_directo_ids = fields.One2many(
        'transito.directo', 'service_order_id', string='Tránsitos Directos',
    )
    transito_directo_count = fields.Integer(
        string='Número de Tránsitos Directos',
        compute='_compute_transito_directo_count',
        store=False,
    )

    # =========================================================
    # CAMPOS FINANCIEROS Y MÉTRICAS
    # =========================================================
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        compute='_compute_currency_id',
        store=True,
    )

    amount_untaxed = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    amount_tax = fields.Monetary(
        string='Impuestos',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    total_weight_kg = fields.Float(
        string='Peso Total (Kg)',
        compute='_compute_amounts',
        store=True,
        help="Suma total de los kilogramos de los residuos de esta orden."
    )

    total_product_qty = fields.Float(
        string='Total Items',
        compute='_compute_amounts',
        store=True,
        help="Suma total de las cantidades (piezas, bultos, servicios) de esta orden."
    )

    lines_count = fields.Integer(
        string='Nº Líneas',
        compute='_compute_amounts',
        store=True,
        help="Cantidad de tipos de residuos/servicios diferentes en la orden."
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    def _get_all_linked_invoices(self):
        self.ensure_one()

        invoices = self.invoice_ids

        if self.name:
            legacy_invoices = self.env['account.move'].search([
                ('invoice_origin', '=', self.name),
                ('move_type', '=', 'out_invoice'),
                ('id', 'not in', invoices.ids)
            ])
            if legacy_invoices:
                invoices |= legacy_invoices

        return invoices

    @api.depends('remolque1_id', 'remolque2_id')
    def _compute_remolques_legacy(self):
        for rec in self:
            rec.remolque1 = rec.remolque1_id.license_plate or rec.remolque1_id.name or False
            rec.remolque2 = rec.remolque2_id.license_plate or rec.remolque2_id.name or False

    @api.depends('transportista_responsable_id')
    def _compute_chofer_id(self):
        for rec in self:
            rec.chofer_id = rec.transportista_responsable_id

    def _inverse_chofer_id(self):
        for rec in self:
            rec.transportista_responsable_id = rec.chofer_id

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.payment_state')
    def _compute_invoicing_status(self):
        for order in self:
            invoices = order._get_all_linked_invoices()
            active_invoices = invoices.filtered(lambda inv: inv.state != 'cancel')

            if not active_invoices:
                order.invoicing_status = 'no'
                continue

            paid_invoices = active_invoices.filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state in ('paid', 'in_payment', 'reversed')
            )
            if paid_invoices:
                order.invoicing_status = 'paid'
                continue

            posted_invoices = active_invoices.filtered(lambda inv: inv.state == 'posted')
            if posted_invoices:
                order.invoicing_status = 'invoiced'
                continue

            draft_invoices = active_invoices.filtered(lambda inv: inv.state == 'draft')
            if draft_invoices:
                order.invoicing_status = 'draft'
                continue

            order.invoicing_status = 'no'

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            invoices = order._get_all_linked_invoices()
            order.invoice_count = len(invoices.filtered(lambda inv: inv.state != 'cancel'))

    @api.depends('transito_directo_ids')
    def _compute_transito_directo_count(self):
        for order in self:
            order.transito_directo_count = len(order.transito_directo_ids)

    @api.depends('sale_order_id', 'sale_order_id.currency_id')
    def _compute_currency_id(self):
        for order in self:
            if order.sale_order_id:
                order.currency_id = order.sale_order_id.currency_id
            else:
                order.currency_id = order.env.company.currency_id

    @api.depends('line_ids.price_unit', 'line_ids.product_uom_qty', 'line_ids.product_id', 'line_ids.weight_kg')
    def _compute_amounts(self):
        for order in self:
            total_untaxed = 0.0
            total_tax = 0.0
            total_weight = 0.0
            total_qty = 0.0
            count_lines = 0

            for line in order.line_ids:
                if line.product_id:
                    price = line.price_unit
                    qty = line.product_uom_qty

                    total_untaxed += price * qty

                    if line.product_id.taxes_id:
                        tax_res = line.product_id.taxes_id.compute_all(
                            price,
                            order.currency_id,
                            qty,
                            product=line.product_id,
                            partner=order.partner_id
                        )
                        total_tax += sum(t.get('amount', 0.0) for t in tax_res.get('taxes', []))

                    total_qty += qty
                    total_weight += line.weight_kg
                    count_lines += 1

            order.amount_untaxed = total_untaxed
            order.amount_tax = total_tax
            order.amount_total = total_untaxed + total_tax
            order.total_weight_kg = total_weight
            order.total_product_qty = total_qty
            order.lines_count = count_lines

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

    def _partner_has_category_name(self, partner, tag_name):
        if not partner or not tag_name:
            return False

        tag_name_normalized = tag_name.strip().lower()

        for category in partner.category_id:
            category_name = (category.name or '').strip().lower()
            if tag_name_normalized in category_name:
                return True

        return False

    def _is_valid_transportista_partner(self, partner):
        return self._partner_has_category_name(partner, TRANSPORTISTA_TAG_NAME)

    def _find_related_contact_with_tag(self, partner, tag_name):
        if not partner:
            return False

        tag = self._get_partner_category_by_name(tag_name)
        if not tag:
            return False

        domain = [
            ('category_id', 'in', [tag.id]),
            '|',
            ('parent_id', '=', partner.id),
            ('id', '=', partner.id)
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

    def _prepare_pickup_location_text(self, partner):
        if not partner:
            return False

        address = partner._display_address() or ''
        address = address.replace('\n', ', ').strip()

        return address or partner.display_name or partner.name or False

    def _get_default_transportista_id(self):
        """
        Define SA Transporte como valor por defecto únicamente si existe
        y tiene la etiqueta Transportista.

        Ya no fuerza SA Transporte en create/write/onchange.
        El selector queda abierto a cualquier contacto etiquetado como Transportista.
        """
        transportista = self.env['res.partner'].sudo().search([
            ('name', '=', DEFAULT_TRANSPORTISTA_NAME),
            ('category_id.name', 'ilike', TRANSPORTISTA_TAG_NAME),
        ], limit=1)

        return transportista.id if transportista else False

    def _normalize_transportista_vals(self, vals):
        """
        Valida que el transportista elegido pertenezca al catálogo permitido.

        Regla de negocio:
        El campo Transportista solo acepta contactos con la etiqueta Transportista.
        """
        if 'transportista_id' not in vals:
            return vals

        if not vals.get('transportista_id'):
            return vals

        transportista = self.env['res.partner'].sudo().browse(vals['transportista_id'])

        if transportista.exists() and not self._is_valid_transportista_partner(transportista):
            raise UserError(_(
                'El contacto seleccionado como Transportista debe tener la etiqueta "%s".'
            ) % TRANSPORTISTA_TAG_NAME)

        return vals

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
                rec.pickup_location = False
                return

            gen = rec._find_related_contact_with_tag(rec.partner_id, 'Generador')
            rec.generador_id = gen.id if gen else False

            if gen:
                rec.pickup_location_id = gen.id
                rec.pickup_location = rec._prepare_pickup_location_text(gen)
            elif rec.pickup_location_id and not rec._is_partner_related_to_client(rec.pickup_location_id, rec.partner_id):
                rec.pickup_location_id = False
                rec.pickup_location = False

            if rec.generador_responsable_id and not rec._is_partner_related_to_client(rec.generador_responsable_id, rec.partner_id):
                rec.generador_responsable_id = False

            if rec.contact_partner_id and not rec._is_partner_related_to_client(rec.contact_partner_id, rec.partner_id):
                rec.contact_partner_id = False

    @api.onchange('generador_id')
    def _onchange_generador_id(self):
        for rec in self:
            if rec.generador_id:
                rec.pickup_location_id = rec.generador_id.id
                rec.pickup_location = rec._prepare_pickup_location_text(rec.generador_id)

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

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            if rec.vehicle_id:
                rec.numero_placa = rec.vehicle_id.license_plate or False
            else:
                rec.numero_placa = False

    @api.onchange('transportista_id')
    def _onchange_transportista_id(self):
        warning = False

        for rec in self:
            if rec.transportista_id and not rec._is_valid_transportista_partner(rec.transportista_id):
                contact_name = rec.transportista_id.display_name

                rec.transportista_id = False
                rec.transportista_responsable_id = False

                warning = {
                    'title': _('Transportista no permitido'),
                    'message': _(
                        'El contacto "%(contact)s" no tiene la etiqueta "%(tag)s".\n\n'
                        'Solo pueden seleccionarse contactos etiquetados como Transportista.'
                    ) % {
                        'contact': contact_name,
                        'tag': TRANSPORTISTA_TAG_NAME,
                    }
                }
                continue

            if rec.transportista_responsable_id and rec.transportista_id:
                ok = (
                    rec.transportista_responsable_id.id == rec.transportista_id.id
                    or rec.transportista_responsable_id.parent_id.id == rec.transportista_id.id
                )
                if not ok:
                    rec.transportista_responsable_id = False

            if not rec.transportista_id:
                rec.transportista_responsable_id = False

        if warning:
            return {'warning': warning}

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

            if 'user_id' not in vals:
                if vals.get('sale_order_id'):
                    sale = self.env['sale.order'].browse(vals['sale_order_id'])
                    vals['user_id'] = sale.user_id.id
                else:
                    vals['user_id'] = self.env.user.id

            self._normalize_transportista_vals(vals)

            if vals.get('partner_id') and not vals.get('generador_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                gen = self._find_related_contact_with_tag(partner, 'Generador')
                vals['generador_id'] = gen.id if gen else False

                if gen:
                    vals['pickup_location_id'] = gen.id
                    vals['pickup_location'] = self._prepare_pickup_location_text(gen)

            elif vals.get('generador_id') and not vals.get('pickup_location_id'):
                gen = self.env['res.partner'].browse(vals['generador_id'])
                if gen.exists():
                    vals['pickup_location_id'] = gen.id
                    vals['pickup_location'] = self._prepare_pickup_location_text(gen)

            if vals.get('contact_partner_id'):
                c = self.env['res.partner'].browse(vals['contact_partner_id'])
                if c:
                    vals.update(self._prepare_contact_legacy_vals(c))

            if vals.get('vehicle_id') and not vals.get('numero_placa'):
                vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                if vehicle.exists():
                    vals['numero_placa'] = vehicle.license_plate or False

            if vals.get('chofer_id') and not vals.get('transportista_responsable_id'):
                vals['transportista_responsable_id'] = vals['chofer_id']
            elif vals.get('transportista_responsable_id') and not vals.get('chofer_id'):
                vals['chofer_id'] = vals['transportista_responsable_id']

        return super().create(vals_list)

    def write(self, vals):
        self._normalize_transportista_vals(vals)

        if 'contact_partner_id' in vals:
            if vals.get('contact_partner_id'):
                partner = self.env['res.partner'].browse(vals['contact_partner_id'])
                if partner.exists():
                    vals.update(self._prepare_contact_legacy_vals(partner))
            else:
                vals.pop('contact_name', None)
                vals.pop('contact_phone', None)

        if 'vehicle_id' in vals and vals.get('vehicle_id'):
            vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
            if vehicle.exists() and 'numero_placa' not in vals:
                vals['numero_placa'] = vehicle.license_plate or False

        if 'generador_id' in vals and vals.get('generador_id'):
            gen = self.env['res.partner'].browse(vals['generador_id'])
            if gen.exists():
                if 'pickup_location_id' not in vals:
                    vals['pickup_location_id'] = gen.id
                if 'pickup_location' not in vals:
                    vals['pickup_location'] = self._prepare_pickup_location_text(gen)

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
        for order in self:
            if order.state not in ('cancel', 'confirmed', 'done'):
                raise UserError(_('Solo se pueden restablecer a borrador órdenes canceladas, confirmadas o completadas.'))
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
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False},
        }

    def action_view_transitos_directos(self):
        self.ensure_one()
        if len(self.transito_directo_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'transito.directo',
                'view_mode': 'form',
                'res_id': self.transito_directo_ids.id,
            }
        return {
            'name': _('Tránsitos Directos'),
            'type': 'ir.actions.act_window',
            'res_model': 'transito.directo',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.transito_directo_ids.ids)],
        }

    def action_recompute_invoicing_status(self):
        self._compute_invoicing_status()
        return True