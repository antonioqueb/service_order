# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_invoice(self):
        """
        Método mejorado para crear facturas desde órdenes de servicio.
        - Valida que no existan facturas duplicadas
        - Copia líneas de producto Y líneas de notas
        - Establece automáticamente la relación service_order_id
        - Marca la orden como facturada
        """
        self.ensure_one()
        
        # ==========================================
        # VALIDACIONES PREVIAS
        # ==========================================
        
        # VALIDACIÓN 1: Verificar que no esté ya facturado
        if self.invoicing_status == 'invoiced':
            raise UserError(_('Esta orden de servicio ya ha sido facturada. No se pueden crear múltiples facturas para la misma orden.'))
        
        # VALIDACIÓN 2: Verificar que no existan facturas previas activas
        existing_invoices = self.env['account.move'].search([
            ('service_order_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel')
        ])
        
        if existing_invoices:
            raise UserError(_('Ya existe una factura para esta orden de servicio: %s') % existing_invoices[0].name)
        
        # VALIDACIÓN 3: Verificar que haya al menos una línea de producto
        if not self.line_ids.filtered('product_id'):
            raise UserError(_("No hay líneas de producto que facturar."))

        # ==========================================
        # PREPARAR VALORES DE LA FACTURA
        # ==========================================
        
        invoice_vals = {
            'move_type':       'out_invoice',
            'partner_id':      self.partner_id.id,
            'invoice_origin':  self.name,  # Mantener referencia al número de orden
            'invoice_date':    fields.Date.context_today(self),
            'invoice_user_id': self.env.uid,
            'invoice_line_ids': [],
            # *** CRÍTICO: Agregar el service_order_id directamente en la creación ***
            'service_order_id': self.id,
        }

        # ==========================================
        # RECORRER TODAS LAS LÍNEAS
        # ==========================================
        # Recorre TODAS las líneas en el orden original (productos Y notas)
        for line in self.line_ids:
            if line.product_id:
                # ========================================
                # LÍNEA DE PRODUCTO
                # ========================================
                # Usar lst_price (precio de lista) del producto
                price = line.product_id.lst_price or 0.0
                
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id':     line.product_id.id,
                    'quantity':       line.product_uom_qty,
                    'price_unit':     price,
                    'name':           line.product_id.display_name,
                    'tax_ids':        [(6, 0, line.product_id.taxes_id.ids)],
                    'product_uom_id': line.product_uom.id,
                    'plan_manejo':    line.plan_manejo,
                }))
            else:
                # ========================================
                # LÍNEA DE NOTA
                # ========================================
                # Línea de nota nativa en la factura (sin producto)
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'display_type': 'line_note',
                    'name':         line.description or '',
                }))

        # ==========================================
        # CREAR LA FACTURA
        # ==========================================
        invoice = self.env['account.move'].create(invoice_vals)
        
        # ==========================================
        # DOBLE SEGURIDAD
        # ==========================================
        # Verificar y establecer nuevamente si no se guardó correctamente
        if not invoice.service_order_id:
            invoice.write({'service_order_id': self.id})
        
        # ==========================================
        # ACTUALIZAR ESTADO DE FACTURACIÓN
        # ==========================================
        # Marcar la orden como facturada inmediatamente
        self.write({'invoicing_status': 'invoiced'})
        
        # ==========================================
        # RETORNAR ACCIÓN PARA ABRIR LA FACTURA
        # ==========================================
        return {
            'name':      _('Factura de Servicio'),
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id':    invoice.id,
            'target':    'current',
        }