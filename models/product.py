# -*- coding: utf-8 -*-

from odoo import api, models


class Product(models.Model):
    _inherit = 'product.product'


    @api.multi
    def get_cart_selection(self, sale_order):
        return 'default'

