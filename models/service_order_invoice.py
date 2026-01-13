# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        """
        Crear factura desde orden de servicio.
        El estado de facturación se calcula automáticamente via compute.
        """
        self.ensure_one()

        # ==========================================
        # VALIDACIONES PREVIAS
        # ==========================================

        # VALIDACIÓN 1: Verificar estado computado (por si hay facturas activas)
        if self.invoicing_status == 'invoiced':
            raise UserError(_('Esta orden de servicio ya tiene una factura activa.'))

        # VALIDACIÓN 2: Verificar que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError(_("No hay líneas de producto que facturar."))

        # ==========================================
        # PREPARAR VALORES DE LA FACTURA
        # ==========================================

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
            'service_order_id': self.id,
        }

        # ==========================================
        # RECORRER TODAS LAS LÍNEAS
        # ==========================================
        for line in self.line_ids:
            if line.product_id:
                price = line.price_unit

                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'price_unit': price,
                    'name': line.product_id.display_name,
                    'tax_ids': [(6, 0, line.product_id.taxes_id.ids)],
                    'product_uom_id': line.product_uom.id,
                    'plan_manejo': line.plan_manejo,
                }))
            else:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name': line.description or '',
                }))

        # ==========================================
        # CREAR LA FACTURA
        # ==========================================
        invoice = self.env['account.move'].create(invoice_vals)

        # Verificar y establecer nuevamente si no se guardó correctamente
        if not invoice.service_order_id:
            invoice.write({'service_order_id': self.id})

        # ==========================================
        # RETORNAR ACCIÓN PARA ABRIR LA FACTURA
        # ==========================================
        return {
            'name': _('Factura de Servicio'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }