from odoo import models, fields
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        self.ensure_one()
        # Asegúrate de que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError("No hay líneas de producto que facturar.")

        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
        }

        # Recorre TODAS las líneas en el orden original
        for line in self.line_ids:
            if line.product_id:
                # Línea de producto
                price = line.product_id.lst_price or 0.0
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id':     line.product_id.id,
                    'quantity':       line.product_uom_qty,
                    'price_unit':     price,
                    'name':           line.product_id.display_name,
                    'tax_ids':        [(6, 0, line.product_id.taxes_id.ids)],
                    'product_uom_id': line.product_uom.id,
                    'plan_manejo':    line.plan_manejo,
                }))
            else:
                # Línea de nota nativa en la factura
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         line.description or '',
                }))

        invoice = self.env['account.move'].create(invoice_vals)
        return {
            'name':      'Factura de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }