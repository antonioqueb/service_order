# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()

        # Propagar ubicación recolección (nuevo selector si existe en sale)
        pickup_partner = getattr(self, 'pickup_location_id', False)
        pickup_location_id = pickup_partner.id if pickup_partner else False

        # Fallback legacy: si existiera un pickup_location tipo char en sale.order
        pickup_location_legacy = getattr(self, 'pickup_location', False)

        # Propagar destinatario final desde venta (si existe final_destination_id)
        final_dest = getattr(self, 'final_destination_id', False)
        destinatario_id = final_dest.id if final_dest else False

        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),

            # NUEVO: Ubicación select + legacy
            'pickup_location_id': pickup_location_id,
            'pickup_location': pickup_location_legacy,

            # NUEVO: Destinatario final propagado
            'destinatario_id': destinatario_id,
        })

        # 2) Copiar líneas (mantener funcionalidad existente)
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                weight_kg = 0.0
                capacity = ""

                # Obtener peso
                if hasattr(line, 'residue_weight_kg') and line.residue_weight_kg:
                    weight_kg = line.residue_weight_kg
                elif hasattr(self, 'opportunity_id') and self.opportunity_id:
                    residue = self.opportunity_id.residue_line_ids.filtered(
                        lambda r: r.product_id == line.product_id
                    )
                    if residue:
                        weight_kg = residue[0].weight_kg
                        capacity = residue[0].capacity if hasattr(residue[0], 'capacity') else 0.0

                # Obtener capacidad
                if hasattr(line, 'residue_capacity') and line.residue_capacity:
                    capacity = line.residue_capacity

                # UoM (Odoo 19)
                uom_id = line.product_uom_id.id if hasattr(line, 'product_uom_id') else False

                # Embalaje (custom en tu módulo de propagate)
                packaging_id_val = False
                if hasattr(line, 'residue_packaging_id') and line.residue_packaging_id:
                    packaging_id_val = line.residue_packaging_id.id

                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': uom_id,
                    'weight_kg': weight_kg,
                    'capacity': capacity,
                    'packaging_id': packaging_id_val,  # uom.uom
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
                    'price_unit': line.price_unit,  # mantiene precio pactado
                }
                self.env['service.order.line'].create(vals)

        # 3) Abrir la vista en modo formulario
        return {
            'name': 'Orden de Servicio',
            'type': 'ir.actions.act_window',
            'res_model': 'service.order',
            'view_mode': 'form',
            'res_id': service.id,
            'target': 'current',
        }

    def action_view_service_orders(self):
        self.ensure_one()
        action = self.env.ref('service_order.action_service_order').read()[0]
        action.update({
            'name': f"Órdenes de Servicio de {self.name}",
            'domain': [('sale_order_id', '=', self.id)],
        })
        return action
