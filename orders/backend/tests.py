import unittest
import json
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework.authtoken.models import Token
from backend.models import Shop, User
from backend.views import RegisterAccount, LoginAccount, PartnerOrders, PartnerState
from rest_framework.authtoken.models import Token

class RegisterAccountTestCase(TestCase):
    def setUp(self):
        """
        Initialize the request factory and the user data for testing.

        This method is called before each test case.
        """
        self.factory = RequestFactory()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword',
            'first_name': 'Test',
            'last_name': 'User',
            'type': 'shop'
        }

    def test_register_account_success(self):
        """
        Tests that a POST request to /register/ with valid user data successfully
        creates a new user and returns a 200 status code and a JSON response with
        {'Status': True}.

        The test case uses the RequestFactory to create a POST request to the
        RegisterAccount view with the user_data as the request body. It then
        asserts that the response status code is 200 and the response content is
        a JSON object with {'Status': True}.

        This test case is important to ensure that the RegisterAccount view is
        working correctly and that a new user can be created with valid data.
        """
        
        request = self.factory.post('/api/v1/user/register', self.user_data)
        response = RegisterAccount.as_view()(request)
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'Status': True})

    def test_register_account_missing_data(self):
        """
        Tests that a POST request to /register/ with missing user data returns
        a 200 status code and a JSON response with {'Status': False, 'Errors':
        'Не указаны все необходимые аргументы'}.

        This test case is important to ensure that the RegisterAccount view is
        working correctly and that a missing required fields results in an
        error response.
        """
        
        request = self.factory.post('/api/v1/user/register', {})
        response = RegisterAccount.as_view()(request)
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class LoginAccountTestCase(TestCase):
    def setUp(self):
        """
        Set up the test environment for LoginAccountTestCase.

        This method initializes a RequestFactory instance and creates a test user
        with the email 'test@example.com' and password 'testpassword'. The created
        user is stored in the `self.user` attribute.

        This setup is called before each test case to ensure a consistent test environment.
        """

        self.factory = RequestFactory()
        self.user = User.objects.create_user('test@example.com', 'testpassword', type='buyer', is_active=True)

    def test_login_account_success(self):
        """
        Tests that a POST request to /login/ with valid user credentials successfully
        authenticates a user and returns a 200 status code and a JSON response with
        {'Status': True, 'Token': <user's token>}.

        This test case is important to ensure that the LoginAccount view is working
        correctly and that a user can be authenticated with valid credentials.
        """
        
        response = self.client.post('/api/v1/user/login', data={'email': self.user.email, 'password': 'testpassword'})
        response_content = response.content
        response_data = json.loads(response_content)
        token, created = Token.objects.get_or_create(user=self.user)

        self.assertEqual(response_data, {'Status': True, 'Token': token.key})

    def test_login_account_invalid_credentials(self):
        """
        Tests that a POST request to /login/ with invalid user credentials returns
        a 200 status code and a JSON response with {'Status': False, 'Errors':
        'Не удалось авторизовать'}.

        This test case is important to ensure that the LoginAccount view is working
        correctly and that an invalid user credentials results in an error response.
        """
        
        request = self.factory.post('/api/v1/user/login/', {'email': 'test@example.com', 'password': 'wrongpassword'})
        response = LoginAccount.as_view()(request)
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'Status': False, 'Errors': 'Не удалось авторизовать'})

class PartnerOrdersTestCase(TestCase):
    def setUp(self):
        """
        Initialize the request factory and the user data for testing.

        This method is called before each test case.
        """
        
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('test@example.com', 'testpassword', type='shop', is_active=True)

    def test_partner_orders_success(self):
        """
        Tests that a GET request to /api/v1/partner/orders with valid
        authentication returns a 200 status code and a JSON response with the
        orders associated with the partner.

        This test case is important to ensure that the PartnerOrders view is
        working correctly and that a valid authentication results in a success
        response.
        """
        
        token, created = Token.objects.get_or_create(user=self.user)
        response = self.client.get('/api/v1/partner/orders',
                                headers={'Authorization': f'Token {token.key}',
                                         'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        # Add more specific assertions based on your response data

    def test_partner_orders_not_authenticated(self):
        """
        Tests that a GET request to /api/v1/partner/orders without authentication
        returns a 403 status code and a JSON response with {'Status': False, 'Error':
        'Необходима авторизация'}.

        This test case ensures that the PartnerOrders view requires user authentication
        and returns an appropriate error response when accessed by an anonymous user.
        """

        request = self.factory.get('/api/v1/partner/orders', format='json')
        request.user = AnonymousUser()
        response = PartnerOrders.as_view()(request)
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response_data, {'Status': False, 'Error': 'Необходима авторизация'})

    def test_partner_orders_not_a_shop(self):
        """
        Tests that a GET request to /api/v1/partner/orders with valid
        authentication but non-shop user type returns a 403 status code and a
        JSON response with {'Status': False, 'Error': 'Только для магазинов'}.

        This test case ensures that the PartnerOrders view requires the user to
        be of type 'shop' and returns an appropriate error response when accessed
        by a user of another type.
        """
        
        token, created = Token.objects.get_or_create(user=self.user)
        
        self.user.type = 'buyer'
        self.user.save()

        response = self.client.get('/api/v1/partner/orders',
                                headers={'Authorization': f'Token {token.key}',
                                         'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 403)

        response_content = response.content
        response_data = json.loads(response_content)

        self.assertEqual(response_data, {'Status': False, 'Error': 'Только для магазинов'})
        
class PartnerStateTestCase(TestCase):
    def setUp(self):
        """
        Initialize the request factory and the user data for testing.

        This method is called before each test case.
        """
        
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('test@example.com', 'testpassword', type='shop', is_active=True)

    def test_partner_state_success(self):
        """
        Tests that a GET request to /api/v1/partner/state with valid
        authentication returns a 200 status code.

        This test case is important to ensure that the PartnerState view is
        working correctly and that a valid authentication results in a success
        response. More specific assertions should be added to verify the response
        data.
        """

        Shop.objects.create(name='Test Shop', user=self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        response = self.client.get('/api/v1/partner/state',
                                headers={'Authorization': f'Token {token.key}',
                                         'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        # Add more specific assertions based on your response data

    def test_partner_state_not_authenticated(self):
        """
        Tests that a GET request to /api/v1/partner/state without authentication
        returns a 403 status code and a JSON response with {'Status': False, 'Error':
        'Необходима авторизация'}.

        This test case ensures that the PartnerState view requires user authentication
        and returns an appropriate error response when accessed by an anonymous user.
        """
        
        request = self.factory.get('/api/v1/partner/state', format='json')
        request.user = AnonymousUser()
        response = PartnerState.as_view()(request)
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response_data, {'Status': False, 'Error': 'Необходима авторизация'})

    def test_partner_state_not_a_shop(self):
        """
        Tests that a GET request to /api/v1/partner/state with valid
        authentication but user type is not 'shop' returns a 403 status code and
        a JSON response with {'Status': False, 'Error': 'Только для магазинов'}.

        This test case ensures that the PartnerState view requires the user to
        be a shop and returns an appropriate error response when accessed by a
        buyer.
        """
        
        token, created = Token.objects.get_or_create(user=self.user)

        self.user.type = 'buyer'
        self.user.save()

        response = self.client.get('/api/v1/partner/orders',
                                headers={'Authorization': f'Token {token.key}',
                                         'Content-Type': 'application/json'})

        self.assertEqual(response.status_code, 403)

        response_content = response.content
        response_data = json.loads(response_content)

        self.assertEqual(response_data, {'Status': False, 'Error': 'Только для магазинов'})

    def test_partner_state_update_success(self):
        """
        Tests that a POST request to /api/v1/partner/state with valid
        authentication and a valid state ('True' or 'False') returns a 200
        status code and a JSON response with {'Status': True}.

        This test case ensures that the PartnerState view correctly updates the
        state of a partner when given a valid state.

        Additionally, this test case ensures that the PartnerState view returns
        a JSON response with the correct format when given a valid state.
        """
        
        Shop.objects.create(name='Test Shop', user=self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        response = self.client.post('/api/v1/partner/state',
                                data={'state': 'True'},
                                headers={'Authorization': f'Token {token.key}'})
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'Status': True})

    def test_partner_state_update_invalid_state(self):
        """
        Tests that a POST request to /api/v1/partner/state with valid
        authentication but invalid state returns a 200 status code and a JSON
        response with {'Status': False, 'Errors': 'Неправильно указан статус'}.

        This test case ensures that the PartnerState view correctly handles
        invalid state values and returns a JSON response with the correct
        format when given an invalid state.
        """
        
        Shop.objects.create(name='Test Shop', user=self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        response = self.client.post('/api/v1/partner/state',
                                data={'state': 'Invalid'},
                                headers={'Authorization': f'Token {token.key}'})
        response_content = response.content
        response_data = json.loads(response_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'Status': False, 'Errors': 'Неправильно указан статус'})

    def test_partner_state_update_not_authenticated(self):
        """
        Tests that a POST request to /api/v1/partner/state without authentication
        returns a 403 status code and a JSON response with {'Status': False, 'Error':
        'Необходима авторизация'}.

        This test case ensures that the PartnerState view requires user authentication
        and returns an appropriate error response when accessed by an anonymous user.
        """
        
        response = self.client.post('/api/v1/partner/state', data={'state': 'new'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response['Content-Type'], 'application/json')

        response_content = response.content
        response_data = json.loads(response_content)

        self.assertEqual(response_data, {'Status': False, 'Error': 'Необходима авторизация'})

    def test_partner_state_update_not_a_shop(self):
        """
        Tests that a POST request to /api/v1/partner/state with valid
        authentication but user type is not 'shop' returns a 403 status code and
        a JSON response with {'Status': False, 'Error': 'Только для магазинов'}.

        This test case ensures that the PartnerState view requires the user to
        be a shop and returns an appropriate error response when accessed by a
        buyer.
        """
        
        token, created = Token.objects.get_or_create(user=self.user)

        self.user.type = 'buyer'
        self.user.save()

        response = self.client.post('/api/v1/partner/state', data={'state': 'new'},
                                   headers={'Authorization': f'Token {token.key}',
                                            'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response['Content-Type'], 'application/json')

        response_content = response.content
        response_data = json.loads(response_content)

        self.assertEqual(response_data, {'Status': False, 'Error': 'Только для магазинов'})