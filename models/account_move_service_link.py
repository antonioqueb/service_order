# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio Origen',
        readonly=False,  # *** EDITABLE: Permite establecer y modificar el valor ***
        copy=False,
        help='Orden de Servicio origen de esta factura',
        tracking=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}  # Solo readonly cuando está posted o cancelada
    )
    
    def write(self, vals):
        # Prevenir cambio de orden de servicio en facturas no en borrador
        if 'service_order_id' in vals:
            for move in self:
                # Solo prevenir el cambio si la factura ya está confirmada Y se intenta cambiar a otra orden diferente
                if move.state in ('posted', 'cancel') and move.service_order_id and vals['service_order_id'] != move.service_order_id.id:
                    raise UserError(_('No se puede cambiar la orden de servicio de una factura confirmada o cancelada.'))
        
        # Ejecutar el write original
        res = super(AccountMove, self).write(vals)
        
        # CRÍTICO: Actualizar el estado de facturación cuando el estado cambia a 'posted'
        if 'state' in vals:
            for move in self:
                if move.service_order_id and move.move_type == 'out_invoice':
                    # Si la factura se confirma (posted), marcar orden como facturada
                    if move.state == 'posted':
                        move.service_order_id.sudo().write({'invoicing_status': 'invoiced'})
                    # Si la factura se cancela, verificar si revertir el estado
                    elif move.state == 'cancel':
                        # Buscar otras facturas no canceladas para esta orden
                        other_invoices = self.env['account.move'].search([
                            ('service_order_id', '=', move.service_order_id.id),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '=', 'posted'),
                            ('id', '!=', move.id)
                        ])
                        # Si no hay otras facturas válidas, marcar como no facturada
                        if not other_invoices:
                            move.service_order_id.sudo().write({'invoicing_status': 'no'})
        
        return res
    
    # Mantener también el override de _post por si acaso
    def _post(self, soft=True):
        """Sobrescribir _post como respaldo para marcar la orden como facturada"""
        res = super(AccountMove, self)._post(soft=soft)
        
        for move in self:
            if move.service_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                move.service_order_id.sudo().write({'invoicing_status': 'invoiced'})
        
        return res

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