# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError
from collections import defaultdict


class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        """
        Crea facturas desde una o múltiples órdenes de servicio.
        Agrupa las órdenes seleccionadas por Cliente y Moneda.
        """
        # Filtrar solo las órdenes que se pueden facturar (Done y sin factura activa)
        orders_to_invoice = self.filtered(lambda so: so.state == 'done' and so.invoicing_status not in ('invoiced', 'paid', 'draft'))

        if not orders_to_invoice:
            if len(self) == 1:
                # Si era una sola y falló, dar error específico
                if self.state != 'done':
                    raise UserError(_("La orden debe estar en estado 'Completado' para facturarse."))
                if self.invoicing_status != 'no':
                    raise UserError(_("Esta orden ya tiene una factura activa."))
            else:
                raise UserError(_("No hay órdenes válidas para facturar en la selección (deben estar completadas y sin facturar)."))

        # Agrupar por (Partner, Currency)
        grouped_orders = defaultdict(lambda: self.env['service.order'])
        for order in orders_to_invoice:
            key = (order.partner_id, order.currency_id)
            grouped_orders[key] |= order

        created_invoices = self.env['account.move']

        # Iterar sobre los grupos y crear facturas
        for (partner, currency), orders in grouped_orders.items():
            
            # Preparar cabecera de factura
            # Usamos los nombres de todas las órdenes para el Origen
            origins = ", ".join(orders.mapped('name'))
            
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'currency_id': currency.id if currency else False,
                'invoice_origin': origins,
                'invoice_date': fields.Date.context_today(self),
                'invoice_user_id': self.env.uid,
                'invoice_line_ids': [],
                # AQUÍ LA CLAVE: Enlazamos todas las órdenes a esta factura
                'service_order_ids': [(6, 0, orders.ids)], 
            }

            # Preparar líneas
            has_lines = False
            for order in orders:
                # Agregar una sección para indicar de qué orden vienen las líneas
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_section',
                    'name': f"Orden: {order.name} ({order.date_order.date()})",
                }))

                for line in order.line_ids:
                    if line.product_id:
                        has_lines = True
                        invoice_vals['invoice_line_ids'].append((0, 0, {
                            'product_id': line.product_id.id,
                            'quantity': line.product_uom_qty,
                            'price_unit': line.price_unit,
                            'name': f"{line.product_id.display_name}" + (f" - {line.name}" if line.name and line.name != line.product_id.name else ""),
                            'tax_ids': [(6, 0, line.product_id.taxes_id.ids)],
                            'product_uom_id': line.product_uom.id,
                            'plan_manejo': line.plan_manejo,
                        }))
                    else:
                        # Notas
                        invoice_vals['invoice_line_ids'].append((0, 0, {
                            'display_type': 'line_note',
                            'name': line.description or '',
                        }))

            if not has_lines:
                # Si un grupo no tiene líneas facturables, lo saltamos con warning en log
                continue

            # Crear factura
            invoice = self.env['account.move'].create(invoice_vals)
            created_invoices |= invoice

        if not created_invoices:
            raise UserError(_("No se generaron facturas (posiblemente las órdenes no tenían líneas de producto)."))

        # Retornar acción
        if len(created_invoices) == 1:
            return {
                'name': _('Factura de Servicio'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': created_invoices.id,
                'target': 'current',
            }
        else:
            return {
                'name': _('Facturas Generadas'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_invoices.ids)],
            }