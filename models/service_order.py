from odoo import models, fields, api

class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Orden de Servicio'
    _inherits = {'sale.order': 'sale_order_id'}

    sale_order_id = fields.Many2one(
        'sale.order', required=True, ondelete='cascade',
        string='Contrato de Venta'
    )

    # Aquí podrías añadir más campos propios de Servicio,
    # pero por herencia ya tienes:
    # - service_frequency, residue_new, requiere_visita, pickup_location
    # - expiration_date, no_delivery, y la lógica de facturación de sale.order

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
        })
        return {
            'name': 'Orden de Servicio',
            'type': 'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id': service.id,
        }
