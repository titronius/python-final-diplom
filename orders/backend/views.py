# from django.shortcuts import render
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse
from requests import get
from rest_framework.views import APIView
from django.core.validators import URLValidator
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from yaml import Loader, load as load_yaml
from backend.models import Category, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop, ConfirmEmailToken
from backend.serializers import ContactSerializer, OrderItemSerializer, OrderSerializer, ProductInfoSerializer, UserSerializer
from backend.signals import new_user_registered, new_order
from django.contrib.auth.password_validation import validate_password
from rest_framework.request import Request
from rest_framework.response import Response
from ujson import loads as load_json
from django.db.models import Q, Sum, F

class RegisterAccount(APIView):
    def post(self, request, *args, **kwargs):
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
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}}, json_dumps_params={'ensure_ascii': False})
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors}, json_dumps_params={'ensure_ascii': False})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
            
class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    
    # Авторизация методом POST
    def post(self, request, *args, **kwargs):
        print(request.data)
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
    def get(self, request: Request, *args, **kwargs):
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
    def post(self, request, *args, **kwargs):
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
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                # return JsonResponse({'Status': True})
                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                
                for category in data['categories']:
                    category, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category.shops.add(shop.id)
                    category.save()
                    
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                
                for good in data['goods']:
                    product, _ = Product.objects.get_or_create(name=good['name'], category_id=good['category'])
                    
                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=good['id'],
                                                              model=good['model'],
                                                              price=good['price'],
                                                              price_rrc=good['price_rrc'],
                                                              quantity=good['quantity'],
                                                              shop_id=shop.id)
                    for key, value in good['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=key)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter.id,
                                                        value=value)
                    
                return JsonResponse({'Status': True})
            
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})                 

class ProductInfoView(APIView):
    """
    A class for searching products.

    Methods:
    - get: Retrieve the product information based on the specified filters.

    Attributes:
    - None
    """

    def get(self, request: Request, *args, **kwargs):
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
    
class Basket(APIView):
    """
    Класс для работы с корзиной пользователя
    """
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
            return JsonResponse({'Status': True, 'Создано объектов': objects_created}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, json_dumps_params={'ensure_ascii': False})
    
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
            return JsonResponse({'Status': True, 'Удалено объектов': deleted_count}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Нету данных'}, json_dumps_params={'ensure_ascii': False})
    
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
                if type(order_item['id']) == int and type(order_item['quantity']) == int:
                    objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                        quantity=order_item['quantity'])
            return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'Status': False, 'Errors': 'Нету данных'}, json_dumps_params={'ensure_ascii': False})

class UserContact(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Необходима авторизация'}, status=403, json_dumps_params={'ensure_ascii': False})
        
        contacts = Contact.objects.filter(
            user_id=request.user.id
        )
        
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
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
    
    def delete(self, request):
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
    
    def put(self, request):
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
