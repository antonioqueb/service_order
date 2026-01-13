# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio Origen',
        readonly=False,
        copy=False,
        help='Orden de Servicio origen de esta factura',
        tracking=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}
    )

    def write(self, vals):
        # Prevenir cambio de orden de servicio en facturas no en borrador
        if 'service_order_id' in vals:
            for move in self:
                if move.state in ('posted', 'cancel') and move.service_order_id and vals['service_order_id'] != move.service_order_id.id:
                    raise UserError(_('No se puede cambiar la orden de servicio de una factura confirmada o cancelada.'))

        return super(AccountMove, self).write(vals)

    def unlink(self):
        """
        Al eliminar facturas, el campo computado invoicing_status
        de la orden de servicio se recalculará automáticamente.
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