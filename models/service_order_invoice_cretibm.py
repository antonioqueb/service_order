# -*- coding: utf-8 -*-
from odoo import models

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        # Disparamos la creación normal de la factura
        action = super().action_create_invoice()
        inv_id = action.get('res_id')
        if inv_id:
            invoice = self.env['account.move'].browse(inv_id)
            # Solo líneas de producto (ignora notas)
            sol_lines = self.line_ids.filtered(lambda l: l.product_id)
            inv_lines = invoice.line_ids.filtered(lambda l: not l.display_type)
            # Zip en orden de creación
            for sol, inv in zip(sol_lines, inv_lines):
                inv.write({
                    'c': sol.c,
                    'r': sol.r,
                    'e': sol.e,
                    't': sol.t,
                    'i': sol.i,
                    'b': sol.b,
                    'm': sol.m,
                })
        return action
