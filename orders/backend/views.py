# from django.shortcuts import render
from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse
from requests import get
from rest_framework.views import APIView
from django.core.validators import URLValidator
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from yaml import Loader, load as load_yaml
from backend.models import Category, Parameter, Product, ProductInfo, ProductParameter, Shop, ConfirmEmailToken
from backend.serializers import UserSerializer
from backend.signals import new_user_registered, new_order
from django.contrib.auth.password_validation import validate_password

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
    def get(self, request, *args, **kwargs):
        """
        Verify a user's email address.

        Args:
            request (Request): The Django request object.
            email (str): The email address to verify.
            token (str): The confirmation token.

        Returns:
            HttpResponse: The response indicating the status of the operation.
        """
        print(kwargs['email'])
        print(kwargs['token'])
        token = ConfirmEmailToken.objects.filter(user__email = kwargs['email'],
                                                 key = kwargs['token'])
        if len(token) == 1:
            token = token[0]
            token.user.is_active = True
            token.user.save()
            token.delete()
            return HttpResponse(f'Успешная регистрация для: {kwargs['email']}')

        return HttpResponse(f'Ошибка в токене или адресе')
class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403, json_dumps_params={'ensure_ascii': False})

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
                    