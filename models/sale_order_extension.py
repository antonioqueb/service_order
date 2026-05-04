# -*- coding: utf-8 -*-
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    service_order_count = fields.Integer(
        string="Órdenes de Servicio",
        compute="_compute_service_order_count",
    )

    def action_create_service_order(self):
        self.ensure_one()

        pickup_partner = getattr(self, 'pickup_location_id', False)
        pickup_location_id = pickup_partner.id if pickup_partner else False

        pickup_location_legacy = getattr(self, 'pickup_location', False)

        final_dest = getattr(self, 'final_destination_id', False)
        destinatario_id = final_dest.id if final_dest else False

        service = self.env['service.order'].create({
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'service_frequency': getattr(self, 'service_frequency', False),
            'residue_new': getattr(self, 'residue_new', False),
            'requiere_visita': getattr(self, 'requiere_visita', False),
            'pickup_location_id': pickup_location_id,
            'pickup_location': pickup_location_legacy,
            'destinatario_id': destinatario_id,
        })

        for line in self.order_line:
            is_display_line = line.display_type in ('line_section', 'line_note')
            has_product = bool(line.product_id)
            has_residue_data = bool(getattr(line, 'residue_name', False))

            if is_display_line:
                _logger.debug("Línea %s omitida: es sección/nota", line.id)
                continue

            if not has_product and not has_residue_data:
                _logger.debug("Línea %s omitida: sin producto ni datos de residuo", line.id)
                continue

            product_id = line.product_id.id if line.product_id else False

            if not product_id and has_residue_data:
                _logger.info(
                    "Línea %s: Creando producto desde residue_name='%s'",
                    line.id,
                    line.residue_name
                )

                if hasattr(line, '_create_service_product'):
                    new_product = line._create_service_product()
                    if new_product:
                        product_id = new_product.id
                        line.write({'product_id': product_id})
                        _logger.info(
                            "Producto creado: %s (ID: %s)",
                            new_product.name,
                            product_id
                        )

            if not product_id:
                _logger.warning(
                    "Línea %s: No se pudo obtener/crear producto. residue_name=%s, create_new_service=%s",
                    line.id,
                    getattr(line, 'residue_name', None),
                    getattr(line, 'create_new_service', None),
                )
                continue

            weight_kg = 0.0
            capacity = ""

            if hasattr(line, 'residue_weight_kg') and line.residue_weight_kg:
                weight_kg = line.residue_weight_kg
            elif hasattr(self, 'opportunity_id') and self.opportunity_id:
                residue = self.opportunity_id.residue_line_ids.filtered(
                    lambda r: r.product_id.id == product_id
                )
                if residue:
                    weight_kg = residue[0].weight_kg
                    capacity = residue[0].capacity if hasattr(residue[0], 'capacity') else ""

            if hasattr(line, 'residue_capacity') and line.residue_capacity:
                capacity = line.residue_capacity

            uom_id = (
                line.product_uom_id.id
                if hasattr(line, 'product_uom_id') and line.product_uom_id
                else False
            )

            packaging_id_val = False
            if hasattr(line, 'residue_packaging_id') and line.residue_packaging_id:
                packaging_id_val = line.residue_packaging_id.id

            manifest_description = (
                (getattr(line, 'manifest_description', False) or '').strip()
                if hasattr(line, 'manifest_description')
                else False
            )

            vals = {
                'service_order_id': service.id,
                'product_id': product_id,
                'name': line.name or getattr(line, 'residue_name', '') or 'Servicio',
                'manifest_description': manifest_description or False,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': uom_id,
                'weight_kg': weight_kg,
                'capacity': capacity,
                'packaging_id': packaging_id_val,
                'residue_type': getattr(line, 'residue_type', False),
                'plan_manejo': getattr(line, 'plan_manejo', False),
                'price_unit': line.price_unit,
            }

            _logger.debug("Creando línea de servicio: %s", vals)
            self.env['service.order.line'].create(vals)

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

    def _compute_service_order_count(self):
        for order in self:
            order.service_order_count = self.env['service.order'].search_count([
                ('sale_order_id', '=', order.id)
            ])