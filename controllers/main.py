# -*- coding: utf-8 -*-

import json
import logging
from werkzeug.exceptions import Forbidden

from odoo import http, tools
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale\
        as WebsiteSaleBase

_logger = logging.getLogger(__name__)


class WebsiteSale(WebsiteSaleBase):

    def _get_vendor_cart_sale_order(self, product, buyer, seller):
        multivendor_cart = request.website.cart_get_orders()
        if seller.id not in multivendor_cart:
            return None

        for so in multivendor_cart[seller.id]['orders']:
            if so.cart_selection == product.get_cart_selection(so):
                return so

        return None


    def _vendor_cart_on_selection(self, product_id):
        product = request.env['product.product'].browse(int(product_id))
        buyer = request.env.user.partner_id
        seller = product.marketplace_seller_id

        if seller:
            so = self._get_vendor_cart_sale_order(product, buyer, seller)
            if so:
                request.session['sale_order_id'] = so.id
            else:
                request.session['sale_order_id'] = None
                buyer.write({'last_website_so_id': None})
        else:
            so = None

        return (so, product, buyer, seller)


    def _vendor_cart_on_new_cart(self, product, buyer, seller):
        so_id = request.session['sale_order_id']
        so = request.env['sale.order'].sudo().browse(so_id)

        so_update = {'marketplace_seller_id': seller.id}

        cart_selection = product.get_cart_selection(so)
        if cart_selection != so.cart_selection:
            so_update['cart_selection'] = cart_selection

        so.write(so_update)

        cart_order_ids = request.session.get('cart_order_ids', [])
        cart_order_ids.append(so_id)
        request.session['cart_order_ids'] = cart_order_ids
        buyer.write({'cart_order_ids': (6, 0, cart_order_ids)})


    @http.route()
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        so, product, buyer, seller = self._vendor_cart_on_selection(product_id)

        response = super(WebsiteSale, self).cart_update(product_id, add_qty,
                set_qty, **kw)

        if not so:
            self._vendor_cart_on_new_cart(product, buyer, seller)

        return response


    @http.route()
    def cart_update_json(self, product_id, line_id=None, add_qty=None,
            set_qty=None, display=True):

        if line_id is not None:
            # ToDo: we assume the product already existed in a cart,
            #       you must not set `set_qty` to add products.
            return super(WebsiteSale, self).cart_update_json(product_id,
                    line_id, add_qty, set_qty, display)

        so, product, buyer, seller = self._vendor_cart_on_selection(product_id)

        response = super(WebsiteSale, self).cart_update_json(product_id,
                line_id, add_qty, set_qty, display)

        if not so:
            self._vendor_cart_on_new_cart(product, buyer, seller)

        return response


class MyWebsiteSale(http.Controller):

    @http.route(['/shop/cart/all'], type='http', auth='public', website=True)
    def cart_all(self, **post):
        multivendor_cart = request.website.cart_get_orders().values()
        vendor_carts = [(so, vc) for vc in multivendor_cart\
                for so in vc['orders']]
                

        try:
            # user selected one cart from many
            submitted_order_id = int(post['order_id'])
        except (KeyError, ValueError, TypeError):
            submitted_order_id = False

        if submitted_order_id:
            for so, vc in vendor_carts:
                if submitted_order_id != so.id:
                    continue

                request.session['sale_order_id'] = submitted_order_id
                return request.redirect('/shop/cart')

        # Remove empty carts
        vendor_carts = [item for item in vendor_carts\
                if item[0] and len(item[0].order_line)]

        new_multivendor_cart = []

        for so, vc in vendor_carts:
            from_currency = so.company_id.currency_id
            to_currency = so.pricelist_id.currency_id
            compute_currency = lambda price: from_currency.compute(price,
                    to_currency)

            cart_data = {
                'compute_currency': compute_currency,
                'order': so,
            }

            for key, value in vc.items():
                if key == 'orders' or key in cart_data:
                    continue

                cart_data[key] = value

            new_multivendor_cart.append(cart_data)

        values = {
            'multivendor_cart': new_multivendor_cart,
        }

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return request.render('multivendor_cart.cart_popover', values,
                    headers={'Cache-Control': 'no-cache'})

        return request.render('multivendor_cart.cart_all', values)
