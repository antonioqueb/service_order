from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio',
        readonly=True,
        copy=False,
        help='Orden de Servicio origen de esta factura'
    )

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        # Llamamos al método original para crear la factura
        action = super(ServiceOrder, self).action_create_invoice()
        invoice = self.env['account.move'].browse(action.get('res_id'))
        # Escribimos el vínculo con esta orden de servicio
        if invoice:
            invoice.write({'service_order_id': self.id})
        return action
