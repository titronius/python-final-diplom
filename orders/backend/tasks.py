from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from requests import get
import requests
from yaml import Loader, load as load_yaml
from backend.models import Product, ProductInfo, Category, Shop, Parameter, ProductParameter
from PIL import Image
from django.core.files.base import ContentFile

@shared_task
def send_email(title, email, text_content, html_content = None):
    """
    Отправляет письмо
    :param title: тема письма
    :param email: адрес, на который отправляется письмо
    :param text_content: текст письма
    :param html_content: html-версия письма
    :return: None
    """
    msg = EmailMultiAlternatives(
        # title:
        title,
        # message:
        text_content,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email]
    )
    if html_content:
        msg.attach_alternative(html_content, "text/html")
    
    msg.send()
    
@shared_task
def do_import(url, user_id):
    """
    Выполняет импорт данных из yaml
    :param url: url до файла yaml
    :param user_id: id пользователя, который выполняет импорт
    :return: None
    """
    
    stream = get(url).content
    data = load_yaml(stream, Loader=Loader)
    shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=user_id)
    
    for category in data['categories']:
        category, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
        category.shops.add(shop.id)
        category.save()
        
    ProductInfo.objects.filter(shop_id=shop.id).delete()
    
    for good in data['goods']:
        product, _ = Product.objects.get_or_create(name=good['name'], category_id=good['category'])
        
        file = None
        if 'photo' in good:
            response = requests.get(good['photo'])
            if response.status_code == 200:
                file_name = f"{good['id']}.{value.split('.')[-1]}"
                file = ContentFile(response.content)
                file.name = file_name
                
                
        product_info = ProductInfo.objects.create(product_id=product.id,
                                                    external_id=good['id'],
                                                    model=good['model'],
                                                    price=good['price'],
                                                    price_rrc=good['price_rrc'],
                                                    quantity=good['quantity'],
                                                    photo=file,
                                                    shop_id=shop.id)
        for key, value in good['parameters'].items():
            parameter, _ = Parameter.objects.get_or_create(name=key)
            ProductParameter.objects.create(product_info_id=product_info.id,
                                            parameter_id=parameter.id,
                                            value=value)

@shared_task
def create_thumbnail(path):
    """
    Создает миниатюру картинки
    :param path: путь до картинки
    :return: None
    """
    img = Image.open(path)
    img.thumbnail((100, 100))
    img.save(path)