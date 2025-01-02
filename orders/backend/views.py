# from django.shortcuts import render
from django.forms import ValidationError
from django.http import JsonResponse
from requests import get
from rest_framework.views import APIView
from django.core.validators import URLValidator
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from yaml import Loader, load as load_yaml
from backend.models import Category, Parameter, Product, ProductInfo, ProductParameter, Shop

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
        if {'email', 'pass'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['pass'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        
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
            
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
                        
                        
                    