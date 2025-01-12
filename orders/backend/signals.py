from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, Order, User
from django.db.models import Sum, F
from backend.serializers import OrderSerializer
from .tasks import send_email

new_user_registered = Signal()

new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """
    # send an e-mail to the user

    msg = EmailMultiAlternatives(
        # title:
        f"Токен для изменения пароля {reset_password_token.user}",
        # message:
        reset_password_token.key,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [reset_password_token.user.email]
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Отправляем письмо с потверждением почты
    """
    if created and not instance.is_active:
        # send an e-mail to the user
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
        
        url_to_confirm = f"{settings.DEFAULT_URL_FOR_MAIL}/user/register/confirm?email={instance.email}&token={token.key}"
        
        text_content = "Подтверждение регистрации"
        
        html_content  =\
        f"""Для подтверждения регистрации перейдите по ссылке:
        <br>
        <a href='{url_to_confirm}'>
        {url_to_confirm}
        </a>
        """
        title = f"Подтверждение регистрации {instance.email}"
        
        result = send_email.delay(title, instance.email, text_content, html_content)
        
        # msg = EmailMultiAlternatives(
        #     # title:
        #     f"Подтверждение регистрации {instance.email}",
        #     # message:
        #     text_content,
        #     # from:
        #     settings.EMAIL_HOST_USER,
        #     # to:
        #     [instance.email]
        # )
        
        # msg.attach_alternative(html_content, "text/html")
        
        # msg.send()


@receiver(new_order)
def new_order_signal(user_id, state, order_id, **kwargs):
    """
    Отправляем письмо при изменении статуса заказа
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)
    title = f"Обновление статуса заказа № {order_id}"
    text_content = f'Новый статус заказа: {state}'
    
    result = send_email.delay(title, user.email, text_content)
    # msg = EmailMultiAlternatives(
    #     # title:
    #     f"Обновление статуса заказа № {order_id}",
    #     # message:
    #     f'Новый статус заказа: {state}',
    #     # from:
    #     settings.EMAIL_HOST_USER,
    #     # to:
    #     [user.email]
    # )
    # msg.send()
    
    if state == 'Новый':
        orders = Order.objects.filter(id=order_id).prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
      
        orders = orders
        serializer = OrderSerializer(orders, many=True)
        
        html_content = f"""
        <h1>Информация о заказе № {serializer.data[0]['id']}</h1>
        <table>
        <tr>
        <th>Продукт</th>
        <th>Количество</th>
        <th>Цена</th>
        <th>Сумма</th>
        </tr>
        """
        for item in serializer.data[0]['ordered_items']:
            html_content += f"""
            <tr>
            <td>{item['product_info']['product']['name']}</td>
            <td>{item['quantity']}</td>
            <td>{item['product_info']['price']}</td>
            <td>{item['quantity'] * item['product_info']['price']}</td>
            </tr>
            """
        html_content += f"""
        </table>
        <br>
        <br>
        <b>Итого: {serializer.data[0]['total_sum']}</b>
        <br>
        <br>
        <b>Контакты:</b>
        <br>
        <b>Телефон:</b> {serializer.data[0]['contact']['phone']}
        <br>
        <b>Город:</b> {serializer.data[0]['contact']['city']}
        <br>
        <b>Улица:</b> {serializer.data[0]['contact']['street']}
        <br>
        <b>Дом:</b> {serializer.data[0]['contact']['house']}
        <br>
        <b>Корпус:</b> {serializer.data[0]['contact']['structure']}
        <br>
        <b>Строение:</b> {serializer.data[0]['contact']['building']}
        <br>
        <b>Квартира:</b> {serializer.data[0]['contact']['apartment']}
        """
        
        title = f"Создан новый заказ № {order_id}"
        text_content = f'Новый статус заказа: {state}'
        
        result = send_email.delay(title, settings.ADMIN_EMAIL, text_content, html_content)
        # msg = EmailMultiAlternatives(
        #     # title:
        #     f"Создан новый заказ № {order_id}",
        #     # message:
        #     f'Новый статус заказа: {state}',
        #     # from:
        #     settings.EMAIL_HOST_USER,
        #     # to:
        #     [settings.ADMIN_EMAIL]
        # )
        
        # msg.attach_alternative(html_content, "text/html")
        
        # msg.send()
        