# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    marketplace_seller_id = fields.Many2one('res.partner', string='Seller',
            copy=False,
            help='If sale order has seller then it will consider as marketplace order else it will consider as simple order')

    cart_selection = fields.Selection(
            [
                ('default', 'Default'),
            ],
            string='Special Purpose Cart/Invoice',
            default='default',
            required=True)
