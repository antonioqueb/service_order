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
        ],
        string="Plan de Manejo",
        help="Método de tratamiento y/o disposición final para el residuo según normatividad ambiental."
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