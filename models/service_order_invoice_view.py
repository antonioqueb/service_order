# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ==============================================================================
# ARCHIVO ANULADO / DEPRECADO
# ==============================================================================
# La lógica para contar facturas (invoice_count) y verlas (action_view_linked_invoices)
# ya está correctamente implementada en 'models/service_order.py' y soporta
# facturación masiva (Many2many).
#
# Este archivo contenía una lógica antigua que sobrescribía la correcta y causaba
# que se perdiera la relación visual al agrupar facturas.
#
# Se mantiene el archivo vacío para evitar errores de importación en __init__.py
# ==============================================================================

# class ServiceOrder(models.Model):
#     _inherit = 'service.order'
#
#     invoice_count = fields.Integer(
#         string='Número de Facturas',
#         compute='_compute_invoice_metrics'
#     )
#
#     @api.depends('name')
#     def _compute_invoice_metrics(self):
#         for rec in self:
#             invoices = self.env['account.move'].search([
#                 ('invoice_origin', '=', rec.name),
#                 ('move_type', '=', 'out_invoice'),
#             ])
#             rec.invoice_count = len(invoices)
#
#     def action_view_linked_invoices(self):
#         self.ensure_one()
#         domain = [
#             ('invoice_origin', '=', self.name),
#             ('move_type', '=', 'out_invoice'),
#         ]
#         # Reusa la acción de cliente (facturas) de account
#         action = self.env.ref('account.action_move_out_invoice_type').read()[0]
#         action.update({
#             'domain': domain,
#             'name': 'Facturas de Servicio',
#         })
#         return action