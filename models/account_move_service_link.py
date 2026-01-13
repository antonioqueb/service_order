# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Cambiamos a Many2many para soportar múltiples órdenes en una factura
    service_order_ids = fields.Many2many(
        'service.order',
        'account_move_service_order_rel', # Nombre tabla intermedia explícito
        'move_id',
        'service_order_id',
        string='Órdenes de Servicio Origen',
        readonly=False,
        copy=False,
        help='Órdenes de Servicio origen de esta factura',
        tracking=True,
    )

    def write(self, vals):
        # Prevenir cambio de orden de servicio en facturas no en borrador
        if 'service_order_ids' in vals:
            for move in self:
                if move.state in ('posted', 'cancel'):
                    raise UserError(_('No se pueden modificar las órdenes de servicio de una factura confirmada o cancelada.'))

        return super(AccountMove, self).write(vals)

    def unlink(self):
        """
        Al eliminar facturas, el campo computado invoicing_status
        de las órdenes de servicio se recalculará automáticamente.
        """
        return super(AccountMove, self).unlink()


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
    )