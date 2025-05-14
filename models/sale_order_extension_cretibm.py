# -*- coding: utf-8 -*-
# models/sale_order_extension_cretibm.py

from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        ServiceOrder = self.env['service.order']
        created_services = ServiceOrder.browse()

        # 1) crear una orden de servicio por cada línea de venta
        for line in self.order_line:
            service = ServiceOrder.create({
                'sale_order_id': self.id,
                'partner_id':    self.partner_id.id,
                'date_order':    fields.Datetime.now(),
            })
            created_services |= service

            # 2) copiar la línea de venta
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

            # 3) propagar flags C-R-E-T-I-B-M
            flags = {f: getattr(line, f, False) for f in ('c', 'r', 'e', 't', 'i', 'b', 'm')}
            if any(flags.values()):
                serv_line.write(flags)

        # 4) si solo hay una creada, abrimos su formulario
        if len(created_services) == 1:
            service = created_services
            return {
                'name':      'Orden de Servicio',
                'type':      'ir.actions.act_window',
                'res_model': 'service.order',
                'view_mode': 'form',
                'res_id':    service.id,
                'target':    'current',
            }

        # 5) si hay varias, mostrar listado
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
