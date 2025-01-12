from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

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