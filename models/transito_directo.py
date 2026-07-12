# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TransitoDirecto(models.Model):
    """Bitácora de tránsitos directos: residuos que SAI transporta del
    generador al destino final sin que pasen por el almacén/inventario de SAI
    (no generan `residuo.recepcion` ni lote). El vínculo con el manifiesto
    ambiental que originó el registro (`manifiesto_id`) se agrega desde
    `manifiesto_ambiental`, que depende de este módulo — este modelo base no
    conoce `manifiesto.ambiental`."""
    _name = 'transito.directo'
    _description = 'Bitácora de Tránsito Directo'
    _order = 'fecha_transito desc'

    name = fields.Char(
        string='Folio', required=True, copy=False, readonly=True,
        default=lambda self: _('Nuevo'),
    )
    service_order_id = fields.Many2one(
        'service.order', string='Orden de Servicio de Origen', ondelete='set null',
    )
    fecha_transito = fields.Date(string='Fecha de Tránsito', default=fields.Date.context_today)

    generador_id = fields.Many2one('res.partner', string='Generador')
    generador_nombre = fields.Char(string='Nombre del Generador')

    destinatario_id = fields.Many2one('res.partner', string='Destinatario Final')
    destinatario_nombre = fields.Char(string='Nombre del Destinatario')

    transportista_id = fields.Many2one('res.partner', string='Transportista')
    transportista_nombre = fields.Char(string='Nombre del Transportista')

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    numero_placa = fields.Char(string='Número de Placa')
    chofer_id = fields.Many2one('res.partner', string='Operador / Chofer')

    observaciones = fields.Text(string='Observaciones')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transito.directo') or _('Nuevo')
        return super().create(vals_list)
