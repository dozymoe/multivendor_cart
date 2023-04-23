# -*- coding: utf-8 -*-

import logging
from odoo import api, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'


    @api.multi
    def cart_get_quantity(self):
        self.ensure_one()
        count = 0
        sale_orders = [so for vc in self.cart_get_orders().values()\
                for so in vc['orders']]

        for so in sale_orders:
            count += so.cart_quantity

        return count

    @api.multi
    def cart_get_orders(self):
        self.ensure_one()
        partner = self.env.user.partner_id
        cart_order_ids = request.session.get('cart_order_ids')
        available_pricelists = self.get_pricelist_available()
        if not cart_order_ids:
            cart_orders = partner.cart_order_ids
            cart_order_ids = [so.id for so in cart_orders if\
                    so.state == 'draft' and\
                    so.pricelist_id in available_pricelists]

            request.session['cart_order_ids'] = cart_order_ids
        else:
            cart_orders = []
            # Test validity
            for so_id in cart_order_ids:
                so = self.env['sale.order'].sudo().browse(so_id).exists() if\
                        so_id else None

                if so and so.state == 'draft' and\
                        so.pricelist_id in available_pricelists:

                    cart_orders.append(so)

            request.session['cart_order_ids'] = [so.id for so in cart_orders]

        multivendor_cart = {}
        if cart_orders:
            for so in reversed(cart_orders): # LIFO
                seller_cart = None
                seller = so.marketplace_seller_id
                if not seller.id:
                    for line in so.order_line:
                        seller = line.marketplace_seller_id
                        if seller:
                            break

                if seller.id:
                    seller_cart = multivendor_cart.get(seller.id)
                    if not seller_cart:
                        seller_cart = {
                            'seller': seller,
                            'orders': [],
                        }
                        multivendor_cart[seller.id] = seller_cart

                if seller_cart:
                    seller_cart['orders'].append(so)

        return multivendor_cart
