#-*- coding: utf-8 -*-
from decimal import Decimal
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.test.testcases import TestCase
from django.core.urlresolvers import reverse

from shop.models.cartmodel import Cart, CartItem
from shop.models.productmodel import Product
from shop.tests.util import Mock
from shop.views.cart import CartDetails
from shop.views.product import ProductDetailView
from shop.util.cart import get_or_create_cart


class ProductDetailViewTestCase(TestCase):
    def create_fixtures(self):
        
        self.product = Product()
        self.product.name = 'test'
        self.product.short_description = 'test'
        self.product.long_description = 'test'
        self.product.unit_price = Decimal('1.0')
        self.product.save()
        
        self.view = ProductDetailView(kwargs={'pk':self.product.id})
    
    def test_01_get_product_returns_correctly(self):
        self.create_fixtures()
        setattr(self.view, 'object', None)
        obj = self.view.get_object()
        inst = isinstance(obj,Product)
        self.assertEqual(inst, True)
        
    def test_02_get_templates_return_expected_values(self):
        self.create_fixtures()
        self.view = ProductDetailView()
        setattr(self.view, 'object', None)
        tmp = self.view.get_template_names()
        self.assertEqual(len(tmp), 1)
        
class CartDetailsViewTestCase(TestCase):
    def create_fixtures(self):
        self.user = User.objects.create(username="test", 
                                        email="test@example.com",
                                        first_name="Test",
                                        last_name = "Tester")
        
        self.cart = Cart.objects.create()
        self.product= Product.objects.create()
        self.item = CartItem.objects.create(cart=self.cart, quantity=1, 
                                            product=self.product)
        
        
    def test_01_get_context_data_works(self):
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.user)
        view = CartDetails(request=request)
        ret = view.get_context_data()
        self.assertNotEqual(ret,None)
        
    def test_02_context_has_as_many_items_as_cart(self):
        self.create_fixtures()
        self.cart.user = self.user
        self.cart.save()
        request = Mock()
        setattr(request, 'user', self.user)
        view = CartDetails(request=request)
        ret = view.get_context_data()
        self.assertNotEqual(ret,None)
        self.assertEqual(len(ret['cart_items']),1)
        self.assertEqual(ret['cart_items'][0], self.item)
        
    def test_03_calling_post_redirects_properly(self):
        self.create_fixtures()
        self.cart.user = self.user
        self.cart.save()
        
        request = Mock()
        setattr(request, 'is_ajax', lambda :False)
        setattr(request, 'user', self.user)
        post={
            'add_item_id':self.product.id,
            'add_item_quantity':1,
        }
        setattr(request, 'POST', post)
        
        view = CartDetails(request=request)
        ret = view.post()
        self.assertTrue(isinstance(ret,HttpResponseRedirect))
        
        ret = view.get_context_data()
        self.assertNotEqual(ret,None)
        self.assertEqual(len(ret['cart_items']),1)
        
        self.assertEqual(ret['cart_items'][0], self.item)
        self.assertEqual(ret['cart_items'][0].quantity, 2)
        
    def test_04_calling_ajax_post_returns_content(self):
        self.create_fixtures()
        self.cart.user = self.user
        self.cart.save()
        
        request = Mock()
        setattr(request, 'is_ajax', lambda :True)
        setattr(request, 'user', self.user)
        post={
            'add_item_id':self.product.id,
            'add_item_quantity':1,
        }
        setattr(request, 'POST', post)
        
        view = CartDetails(request=request)
        ret = view.post()
        self.assertTrue(isinstance(ret,HttpResponse))
        
        ret = view.get_context_data()
        self.assertNotEqual(ret,None)
        self.assertEqual(len(ret['cart_items']),1)
        
        self.assertEqual(ret['cart_items'][0], self.item)
        self.assertEqual(ret['cart_items'][0].quantity, 2)



class CartViewTestCase(TestCase):

    def setUp(self):
        self.product = Product.objects.create()

    def add_product_to_cart(self, product):
        post = {
            'add_item_id':self.product.id,
            'add_item_quantity':1,
        }
        return self.client.post(reverse('cart_item_add'), post)

    def get_cart(self):
        # NOTE: it would be better to use get_or_create_cart(request)
        # dont know how to get request
        response = self.client.get(reverse('cart'))
        return response.context["cart"]

    def assertCartHasItems(self, expected):
        cart = self.get_cart()
        count = sum([cart_item.quantity for cart_item in cart.items.all()])
        self.assertEqual(count, expected)

    def test_01_cart(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_02_cart_item_add(self):
        response = self.add_product_to_cart(self.product)
        self.assertEqual(response.status_code, 302)
        self.assertCartHasItems(1)

    def test_03_cart_delete(self):
        self.add_product_to_cart(self.product)

        url = reverse('cart_delete')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 302)
        self.assertCartHasItems(0)

    def test_04_cart_update(self):
        self.add_product_to_cart(self.product)

        cart = self.get_cart()
        post = { 'update_item-%d' % cart.items.all()[0].pk : '5' }
        response = self.client.post(reverse("cart_update"), post)
        self.assertEqual(response.status_code, 302)
        self.assertCartHasItems(5)

    def test_05_cart_item_update(self):
        self.add_product_to_cart(self.product)

        cart = self.get_cart()
        cart_item_id = cart.items.all()[0].pk
        url = reverse('cart_item', kwargs={'id': cart_item_id})
        post = { 'item_quantity': "5" }
        response = self.client.put(url, post, 
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertCartHasItems(5)

    def test_06_cart_item_delete(self):
        self.add_product_to_cart(self.product)

        cart = self.get_cart()
        cart_item_id = cart.items.all()[0].pk
        cart_item_id = "1"
        url = reverse('cart_item', kwargs={'id': cart_item_id})
        response = self.client.delete(url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertCartHasItems(0)
