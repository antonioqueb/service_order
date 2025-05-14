# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # 1) Crea la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id':    self.partner_id.id,
            'date_order':    fields.Datetime.now(),
        })
        # 2) Copia cada línea de venta a línea de servicio
        for line in self.order_line:
            self.env['service.order.line'].create({
                'service_order_id': service.id,
                'product_id':       line.product_id.id,
                'name':             line.name,                  # la nota/descripción
                'product_uom_qty':  line.product_uom_qty,
                'product_uom':      line.product_uom.id,
                # packaging_id se omite porque sale.order.line no tiene ese campo
                'residue_type':     getattr(line, 'residue_type', False),
            })
        # 3) Abre la vista de la nueva orden de servicio
        return {
            'name':      'Orden de Servicio',
            'type':      'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id':    service.id,
            'target':    'current',
        }
