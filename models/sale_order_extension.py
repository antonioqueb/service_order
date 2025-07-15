# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_service_order(self):
        self.ensure_one()
        # 1) Crear la orden de servicio
        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),
            'pickup_location': getattr(self, 'pickup_location', False),
        })
        
        # 2) Copiar líneas - ahora propagando CORRECTAMENTE el peso
        for line in self.order_line:
            # Solo procesar líneas que NO sean notas y tengan producto
            if line.display_type != 'line_note' and line.product_id:
                # NUEVO: Obtener el peso desde los campos de la línea de venta
                weight_kg = 0.0
                
                # Primero intentar desde los campos específicos de residuo en la línea
                if hasattr(line, 'residue_weight_kg') and line.residue_weight_kg:
                    weight_kg = line.residue_weight_kg
                # Si no, buscar en el lead relacionado
                elif hasattr(self, 'opportunity_id') and self.opportunity_id:
                    # Buscar el residuo que corresponde a este producto
                    residue = self.opportunity_id.residue_line_ids.filtered(
                        lambda r: r.product_id == line.product_id
                    )
                    if residue:
                        weight_kg = residue[0].weight_kg
                
                # Determinar la unidad de medida correcta
                # Prioridad: 1) Embalaje, 2) UoM del producto, 3) UoM de la línea
                uom_id = line.product_uom.id
                if line.product_packaging_id:
                    # Si hay embalaje, usar la UoM del producto base
                    uom_id = line.product_id.uom_id.id
                elif line.product_id.uom_id:
                    uom_id = line.product_id.uom_id.id
                
                vals = {
                    'service_order_id': service.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': uom_id,
                    'weight_kg': weight_kg,  # CORREGIDO: Propagación correcta del peso
                    'packaging_id': line.product_packaging_id.id if line.product_packaging_id else False,  # NUEVO: Propagar embalaje
                    'residue_type': getattr(line, 'residue_type', False),
                    'plan_manejo': getattr(line, 'plan_manejo', False),
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