# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Para poder guardar y mostrar C-R-E-T-I-B-M en las líneas de factura
    c = fields.Boolean(string='C')
    r = fields.Boolean(string='R')
    e = fields.Boolean(string='E')
    t = fields.Boolean(string='T')
    i = fields.Boolean(string='I')
    b = fields.Boolean(string='B')
    m = fields.Boolean(string='M')
