# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    clasificacion_residuo = fields.Selection([
        ('biologico_infeccioso', 'Biológico-Infeccioso'),
        ('corrosivo', 'Corrosivo'),
        ('reactivo', 'Reactivo'),
        ('explosivo', 'Explosivo'),
        ('toxico', 'Tóxico'),
        ('inflamable', 'Inflamable'),
        ('biologico', 'Biológico'),
    ], string='Clasificación del Residuo')
    
    envase_tipo_default = fields.Selection([
        ('tambor', 'Tambor'),
        ('contenedor', 'Contenedor'),
        ('tote', 'Tote'),
        ('tarima', 'Tarima'),
        ('saco', 'Saco'),
        ('caja', 'Caja'),
        ('bolsa', 'Bolsa'),
        ('tanque', 'Tanque'),
        ('otro', 'Otro'),
    ], string='Tipo de Envase por Defecto')
    
    envase_capacidad_default = fields.Float(
        string='Capacidad de Envase por Defecto',
        help='Capacidad del envase en la unidad correspondiente'
    )