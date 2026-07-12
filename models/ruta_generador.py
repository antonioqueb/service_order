# -*- coding: utf-8 -*-
from odoo import fields, models


class RutaGenerador(models.Model):
    """Catálogo formal de rutas por generador (origen, destino, distancia y
    tiempo estimado). Registro puramente de referencia/consulta: no se vincula
    a órdenes de servicio, manifiestos ni planeación logística — vive con su
    propio menú, independiente del resto de la suite."""
    _name = 'ruta.generador'
    _description = 'Ruta por Generador'
    _order = 'generador_id, name'

    name = fields.Char(string='Nombre de la Ruta', required=True)
    generador_id = fields.Many2one('res.partner', string='Generador', required=True)

    origen = fields.Char(string='Origen')
    destino = fields.Char(string='Destino')
    distancia_km = fields.Float(string='Distancia (km)')
    tiempo_estimado = fields.Float(string='Tiempo Estimado (horas)')

    observaciones = fields.Text(string='Observaciones')
    active = fields.Boolean(string='Activa', default=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
