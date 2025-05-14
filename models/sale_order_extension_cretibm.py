# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        ServiceOrder = self.env['service.order']
        # 1) Crear UNA única orden de servicio para esta venta
        service = ServiceOrder.create({
            'sale_order_id': self.id,
            'partner_id':    self.partner_id.id,
            'date_order':    fields.Datetime.now(),
        })
        # 2) Copiar cada línea de la venta en una línea de servicio
        for line in self.order_line:
            vals = {
                'service_order_id': service.id,
                'name':             line.name,
            }
            if line.product_id:
                vals.update({
                    'product_id':      line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom':     line.product_uom.id,
                    'residue_type':    getattr(line, 'residue_type', False),
                })
            serv_line = self.env['service.order.line'].create(vals)
            # 3) Propagar flags C-R-E-T-I-B-M si existen en la línea de venta
            flags = {f: getattr(line, f, False) for f in ('c','r','e','t','i','b','m')}
            if any(flags.values()):
                serv_line.write(flags)
        # 4) Abrir directamente el formulario de la orden de servicio
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
