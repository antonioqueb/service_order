# -*- coding: utf-8 -*-
from odoo import models, fields

class ServiceOrderLine(models.Model):
    _inherit = 'service.order.line'

    # Campos C-R-E-T-I-B-M
    c = fields.Boolean(string='C')
    r = fields.Boolean(string='R')
    e = fields.Boolean(string='E')
    t = fields.Boolean(string='T')
    i = fields.Boolean(string='I')
    b = fields.Boolean(string='B')
    m = fields.Boolean(string='M')
