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
        })
        # 2) Copiar tanto líneas con producto como líneas de nota
        for line in self.order_line:
            vals = {
                'service_order_id': service.id,
                'name':             line.name,  # siempre copiamos la descripción
            }
            if line.product_id:
                # solo si viene producto, agregamos los campos relacionados
                vals.update({
                    'product_id':       line.product_id.id,
                    'product_uom_qty':  line.product_uom_qty,
                    'product_uom':      line.product_uom.id,
                    'residue_type':     getattr(line, 'residue_type', False),
                    'plan_manejo':      getattr(line, 'plan_manejo', False),
                    # packaging_id se omite porque sale.order.line no lo tiene
                })
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