# from django.shortcuts import render
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse
from requests import get
from rest_framework.views import APIView
from django.core.validators import URLValidator
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from backend.models import STATE_CHOICES, Category, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop, ConfirmEmailToken
from backend.serializers import ContactSerializer, OrderItemSerializer, OrderSerializer, ProductInfoSerializer, ShopSerializer, UserSerializer
from backend.signals import new_user_registered, new_order
from django.contrib.auth.password_validation import validate_password
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import Q, Sum, F
from distutils.util import strtobool
from .tasks import do_import
from backend.schema import BasketAddResponse, BasketAddUpdateRequest, BasketBaseRequest, BasketDeleteResponse, BasketUpdateResponse, ContactRequest, ContactResponse, LoginAccountRequest, LoginAccountResponse, OrderConfirmRequest, OrderResponse, OrderUpdateRequest, PartnerStateRequest, PartnerStateResponse, PartnerUpdateRequest, PartnerUpdateResponse, RegisterAccountRequest, RegisterAccountResponse

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

class RegisterAccount(APIView):
    @extend_schema(request=RegisterAccountRequest,
                   responses={'200:': RegisterAccountResponse},
                   tags=['RegisterAccount'])
    def post(self, request):
        """
        Process a POST request and create a new user.

        Args:
            request (Request): The Django request object.

        Returns:
            JsonResponse: The response indicating the status of the operation and any errors.
        """
        if {'first_name', 'last_name', 'email', 'password'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}}, json_dumps_params={'ensure_ascii': False}, status=400)
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors}, json_dumps_params={'ensure_ascii': False}, status=400)

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False}, status=400)
            
class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    # Авторизация методом POST
    @extend_schema(request=LoginAccountRequest,
                   responses={
                       '200:': LoginAccountResponse},
                   tags=['LoginAccount'])
    def post(self, request):
        """
        Authenticate a user.

        Args:
            request (Request): The Django request object.

        Returns:
            JsonResponse: The response indicating the status of the operation and any errors.
        """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'}, json_dumps_params={'ensure_ascii': False})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
    
class ConfirmToken(APIView):
    @extend_schema(parameters=[
        OpenApiParameter('email', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('token', OpenApiTypes.STR, OpenApiParameter.PATH)
    ],
                   responses={'200': OpenApiTypes.STR},
                   tags=['ConfirmToken'])
    def get(self, request: Request):
        """
        Verify a user's email address.

        Args:
            request (Request): The Django request object.
            email (str): The email address to verify.
            token (str): The confirmation token.

        Returns:
            HttpResponse: The response indicating the status of the operation.
        """
        email = request.query_params.get('email')
        token = request.query_params.get('token')
        
        if email and token:
            token = ConfirmEmailToken.objects.filter(user__email = email,
                                                    key = token)
            if len(token) == 1:
                token = token[0]
                token.user.is_active = True
                token.user.save()
                token.delete()
                return HttpResponse(f'Успешная регистрация для: {email}')

        return HttpResponse(f'Ошибка в токене или адресе')
class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    @extend_schema(request=PartnerUpdateRequest,
                   responses={'200:': PartnerUpdateResponse},
                   tags=['PartnerUpdate'])
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                result = do_import.delay(url, request.user.id)
                return JsonResponse({'Status': True})
            
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})                 

class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
     Methods:
    - get: Retrieve the orders associated with the authenticated partner.

    Attributes:
    - None
    """

    @extend_schema(responses={'200:': OrderSerializer(many=True)},
                   tags=['PartnerOrders'])
    def get(self, request):
        """
        Retrieve the orders associated with the authenticated partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the orders associated with the partner.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': False, 'Error': 'Только для магазинов'}: If the user is not a shop.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'},\
                status=403, json_dumps_params={'ensure_ascii': False})

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},\
                status=403, json_dumps_params={'ensure_ascii': False})
        
        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

class PartnerState(APIView):
    """
    A class for managing partner state.

    Methods:
    - get: Retrieve the state of the partner.

    Attributes:
    - None
    """
    # получить текущий статус
    @extend_schema(responses={
        '200:': ShopSerializer
    },
                   tags=['PartnerState'])
    def get(self, request):
        """
        Retrieve the state of the partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the state of the partner.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'},\
                status=403, json_dumps_params={'ensure_ascii': False})

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},\
                status=403, json_dumps_params={'ensure_ascii': False})

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    @extend_schema(request=PartnerStateRequest,
                   responses={'200:': PartnerStateResponse},
                   tags=['PartnerState'])
    def post(self, request):
        """
        Update the state of a partner.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'},\
                status=403, json_dumps_params={'ensure_ascii': False})

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'},\
                status=403, json_dumps_params={'ensure_ascii': False})
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан статус'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'},\
            json_dumps_params={'ensure_ascii': False})

class ProductInfoView(APIView):
    """
    A class for searching products.

    Methods:
    - get: Retrieve the product information based on the specified filters.

    Attributes:
    - None
    """
    @extend_schema(parameters=[
        OpenApiParameter('shop_id', OpenApiTypes.INT, required=False),
        OpenApiParameter('category_id', OpenApiTypes.INT, required=False),
        OpenApiParameter('category_name', OpenApiTypes.STR, required=False),
        OpenApiParameter('product_name', OpenApiTypes.STR, required=False),
        OpenApiParameter('model', OpenApiTypes.STR, required=False)
        ],
                   responses={'200:': ProductInfoSerializer(many=True)},
                   tags=['ProductInfoView'])
    def get(self, request: Request):
        """
        Retrieve the product information based on the specified filters.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the product information.
        """
        query = Q(shop__state=True)
        params = dict(request.query_params)
        
        if 'shop_id' in params:
            query &= Q(shop_id=params['shop_id'][0])

        if 'category_id' in params:
            query &= Q(product__category_id=params['category_id'][0])
            
        if 'category_name' in params:            
            query &= Q(product__category__name__contains=params['category_name'][0])
            
        if 'product_name' in params:
            query &= Q(product__name__contains=params['product_name'][0])
            
        if 'model' in params:
            query &= Q(model__contains=params['model'][0])

        # фильтруем и отбрасываем дубликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)
    
class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """
    @extend_schema(responses={'200:': OrderSerializer(many=True)},
                   tags=['BasketView'])
    def get(self, request):
        """
        Retrieve the items in the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the items in the user's basket.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)
    
    @extend_schema(request=BasketAddUpdateRequest(many=True),
                   responses={'200:': BasketAddResponse},
                   tags=['BasketView'])
    def post(self, request):
        """
        Add items to the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})

        items_dict = request.data.get('items')
        if items_dict:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            objects_created = 0
            for order_item in items_dict:
                order_item.update({'order': basket.id})
                serializer = OrderItemSerializer(data=order_item)
                if serializer.is_valid():
                    try:
                        serializer.save()
                    except IntegrityError as error:
                        return JsonResponse({'Status': False, 'Errors': str(error)}, json_dumps_params={'ensure_ascii': False})
                    else:
                        objects_created += 1
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})
            return JsonResponse({'Status': True, 'objects_created': objects_created}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
    
    @extend_schema(responses={'200:': BasketDeleteResponse},
                   tags=['BasketView'])
    def delete(self, request):
        """
        Remove items from the user's basket.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        items_dict = request.data.get('items')
        if items_dict:
            deleted_count = 0
            basket = Order.objects.filter(user_id=request.user.id, state='basket').first()
            if basket:
                for item in items_dict:
                    item = OrderItem.objects.filter(order_id=basket.id, product_info_id=item['product_info']).first()
                    if item:
                        item.delete()
                        deleted_count += 1
            return JsonResponse({'Status': True, 'deleted_count': deleted_count}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Нету данных'}, json_dumps_params={'ensure_ascii': False})
    
    @extend_schema(request=BasketAddUpdateRequest(many=True),
                   responses={'200:': BasketUpdateResponse},
                   tags=['BasketView'])
    def put(self, request):
        """
        Update the quantity of items in the user's basket.

        Args:
        - request (Request): The Django request object containing the user and items data.

        Returns:
        - JsonResponse: A JSON response indicating the status of the update operation.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': True, 'Обновлено объектов': objects_updated}: If the update is successful, 
            where objects_updated is the number of updated items.
        - {'Status': False, 'Errors': 'Нету данных'}: If no items data is provided in the request.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        items_dict = request.data.get('items')
        if items_dict:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            objects_updated = 0
            for order_item in items_dict:
                if type(order_item['product_info']) == int and type(order_item['quantity']) == int:
                    objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['product_info']).update(
                        quantity=order_item['quantity'])
            return JsonResponse({'Status': True, 'objects_updated': objects_updated}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Нету данных'}, json_dumps_params={'ensure_ascii': False})

class ContactView(APIView):
    @extend_schema(responses={'200:': ContactSerializer(many=True)},
                   tags=['ContactView'])
    def get(self, request):
        """
        Retrieve the contact information of the authenticated user.

        Args:
        - request (Request): The Django request object.

        Returns:
        - Response: The response containing the contact information.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        contacts = Contact.objects.filter(
            user_id=request.user.id
        )
        
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    @extend_schema(request=ContactRequest,
                   responses={'200:': ContactResponse},
                   tags=['ContactView'])
    def post(self, request):
        """
        Create a new contact for the authenticated user.

        Args:
        - request (Request): The Django request object containing the user and contact data.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}: If not all required arguments are provided.
        - {'Status': False, 'Errors': serializer.errors}: If the contact data is invalid.
        - {'Status': True}: If the contact is created successfully.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        if {'city', 'street', 'phone'}.issubset(request.data):
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})
            
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
    
    @extend_schema(responses={'200:': ContactResponse},
                   tags=['ContactView'])
    def delete(self, request):
        """
        Delete a contact of the authenticated user.

        Args:
        - request (Request): The Django request object containing the user and contact data.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': False}: If no contact with the given id exists or the contact is not related to the user.
        - {'Status': True}: If the contact is deleted successfully.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        if 'id' in request.data:
            contact = Contact.objects.filter(
                user_id=request.user.id, id=request.data['id']
            ).first()
            if contact:
                contact.delete()
                return JsonResponse({'Status': True})
        
        return JsonResponse({'Status': False})
    
    @extend_schema(request=ContactRequest,
                   responses={'200:': ContactResponse},
                   tags=['ContactView'])
    def put(self, request):
        """
        Update the contact information of the authenticated user.

        Args:
        - request (Request): The Django request object containing the user and contact data.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': False}: If no contact with the given id exists or the contact is not related to the user.
        - {'Status': True}: If the contact is updated successfully.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        if 'id' in request.data:
            contact = Contact.objects.filter(
                user_id=request.user.id, id=request.data['id']
            ).first()
            if contact:
                serializer = ContactSerializer(contact, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({'Status': True})
                else:
                     return JsonResponse({'Status': False, 'Errors': serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    
class OrderView(APIView):
    @extend_schema(parameters=[
        OpenApiParameter('id', OpenApiTypes.INT, required=False),
        OpenApiParameter('state', OpenApiTypes.STR, required=False),
        ],
                   responses={'200:': OrderSerializer(many=True)},
                   tags=['OrderView'])
    def get(self, request):
        """
        Retrieve the orders associated with the authenticated user.

        Args:
        - request (Request): The Django request object containing the query parameters.

        Returns:
        - JsonResponse: The response containing the orders associated with the user.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        params = dict(request.query_params)
        
        orders = Order.objects.filter(user_id=request.user.id)
        
        if 'id' in params:
            orders = orders.filter(id=params['id'][0])
        if 'state' in params:
            orders = orders.filter(state=params['state'][0])
            
        orders = orders.prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @extend_schema(request=OrderConfirmRequest,
                   responses={'200:': OrderResponse},
                   tags=['OrderView'])
    def post(self, request):
        """
        Create a new order and send a notification.

        Args:
        - request (Request): The Django request object containing the user and contact data.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        - {'Status': False, 'Error': 'Необходима авторизация'}: If the user is not authenticated.
        - {'Status': False, 'Errors': 'Неправильно указаны аргументы'}: If the order id is invalid or the contact id is invalid.
        - {'Status': False, 'Errors': 'Заказ уже подтверждён'}: If the order is already confirmed.
        - {'Status': True}: If the order is created successfully.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})

        if {'contact_id', 'order_id'}.issubset(request.data):
            order = Order.objects.filter(user_id=request.user.id, id=request.data['order_id']).first()
            if order:
                if order.state != 'basket':
                    return JsonResponse({'Status': False, 'Errors': 'Заказ уже подтверждён'}, json_dumps_params={'ensure_ascii': False})
                contact = Contact.objects.filter(user_id=request.user.id, id=request.data['contact_id']).first()
                if not contact:
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указан id контакта'}, json_dumps_params={'ensure_ascii': False})
                order.contact_id = request.data['contact_id']
                order.state = 'new'
                order.save()
                new_order.send(sender=self.__class__, user_id=request.user.id, state='Новый', order_id=request.data['order_id'])
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
    
    @extend_schema(request=OrderUpdateRequest,
                   responses={'200:': OrderResponse},
                   tags=['OrderView'])
    def put(self, request):
        if not request.user.is_superuser:
            return JsonResponse({'Status': False, 'Error': 'Доступно только администраторам'}, status=403, json_dumps_params={'ensure_ascii': False})

        if {'order_id', 'state'}.issubset(request.data):
            order = Order.objects.filter(id=request.data['order_id']).first()
            if order:
                state_name = ''
                for item in STATE_CHOICES:
                    if item[0] == request.data['state']:
                        state_name = item[1]
                        break
                if state_name:
                    order.state = request.data['state']
                    order.save()
                    new_order.send(sender=self.__class__, user_id=order.user.id, state=state_name, order_id=request.data['order_id'])
                    return JsonResponse({'Status': True})
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан статус'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'}, json_dumps_params={'ensure_ascii': False})