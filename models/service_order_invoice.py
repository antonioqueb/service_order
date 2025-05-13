from odoo import models, fields, api
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        """Genera una factura de cliente a partir de la orden de servicio."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError("No hay líneas de servicio para facturar.")
        # Prepara encabezado de factura
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
        }
        # Itera líneas de servicio para poblar líneas de factura
        for line in self.line_ids:
            price = line.product_id.lst_price or 0.0
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id':    line.product_id.id,
                'quantity':      line.product_uom_qty,
                'price_unit':    price,
                'name':          line.product_id.display_name,
                'tax_ids':       [(6, 0, line.product_id.taxes_id.ids)],
                'product_uom_id': line.product_uom.id,
            }))
        # Crea la factura
        invoice = self.env['account.move'].create(invoice_vals)
        # Devuelve acción para abrir la factura
        return {
            'name':      'Factura de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode':'form',
            'res_id':    invoice.id,
            'target':    'current',
        }
