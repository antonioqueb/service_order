# -*- coding: utf-8 -*-
# models/sale_order_extension_cretibm.py

from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        ServiceOrder = self.env['service.order']
        created_services = ServiceOrder.browse()

        for line in self.order_line:
            # 1) Crear una orden de servicio por cada línea de venta
            service = ServiceOrder.create({
                'sale_order_id': self.id,
                'partner_id':    self.partner_id.id,
                'date_order':    fields.Datetime.now(),
            })
            created_services |= service

            # 2) Copiar la línea de venta en la orden de servicio
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

            # 3) Propagar los flags C-R-E-T-I-B-M
            flags = {f: getattr(line, f, False) for f in ('c', 'r', 'e', 't', 'i', 'b', 'm')}
            if any(flags.values()):
                serv_line.write(flags)

        # 4) Devolver acción mostrando todas las órdenes creadas
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name':      f"Órdenes de Servicio de {self.name}",
            'view_mode': 'tree,form',
            'domain':    [('id', 'in', created_services.ids)],
        })
        return action

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name':   f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action
