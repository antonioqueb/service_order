# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError
# good practice: importar excepciones específicas

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        self.ensure_one()
        # 1) Validación de líneas de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError("No hay líneas de producto que facturar.")

        # 2) Preparamos el dict de creación, inyectando C-R-E-T-I-B-M
        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
        }
        for sol in self.line_ids:
            if sol.product_id:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id':     sol.product_id.id,
                    'quantity':       sol.product_uom_qty,
                    'price_unit':     sol.product_id.lst_price or 0.0,
                    'name':           sol.product_id.display_name,
                    'tax_ids':        [(6, 0, sol.product_id.taxes_id.ids)],
                    'product_uom_id': sol.product_uom.id,
                    # ← aquí propagamos los flags
                    'c': sol.c,
                    'r': sol.r,
                    'e': sol.e,
                    't': sol.t,
                    'i': sol.i,
                    'b': sol.b,
                    'm': sol.m,
                }))
            else:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         sol.description or '',
                }))

        # 3) Creamos la factura
        invoice = self.env['account.move'].create(invoice_vals)
        # 4) Devolvemos la acción para abrirla en formulario
        return {
            'name':      'Factura de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }
