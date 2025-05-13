from odoo import models, fields, api

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    invoice_count = fields.Integer(
        string='Número de Facturas',
        compute='_compute_invoice_metrics'
    )

    @api.depends('name')
    def _compute_invoice_metrics(self):
        for rec in self:
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', rec.name),
                ('move_type', '=', 'out_invoice'),
            ])
            rec.invoice_count = len(invoices)

    def action_view_linked_invoices(self):
        self.ensure_one()
        domain = [
            ('invoice_origin', '=', self.name),
            ('move_type', '=', 'out_invoice'),
        ]
        # Reusa la acción de cliente (facturas) de account
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action.update({
            'domain': domain,
            'name': 'Facturas de Servicio',
        })
        return action
