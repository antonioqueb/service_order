# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id':    self.partner_id.id,
            'date_order':    fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),
            'pickup_location': getattr(self, 'pickup_location', False),
        })
        
        # 2) Copiar líneas - ahora solo servicios reales
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
                }
                self.env['service.order.line'].create(vals)
        
        # 3) Abrir la vista en modo formulario
        return {
            'name':      'Orden de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id':    service.id,
            'target':    'current',
        }

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name':   f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action