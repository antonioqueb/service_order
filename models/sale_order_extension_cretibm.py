# -*- coding: utf-8 -*-
from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        # Llamamos al original, que ya crea la service.order + líneas básicas
        action = super().action_create_service_order()
        service_id = action.get('res_id')
        if service_id:
            service = self.env['service.order'].browse(service_id)
            # Propagamos C-R-E-T-I-B-M de cada sale.order.line a service.order.line
            for sale_line, serv_line in zip(self.order_line, service.line_ids):
                serv_line.write({
                    'c': sale_line.c,
                    'r': sale_line.r,
                    'e': sale_line.e,
                    't': sale_line.t,
                    'i': sale_line.i,
                    'b': sale_line.b,
                    'm': sale_line.m,
                })
        return action
