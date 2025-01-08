from django.urls import path
from backend.views import BasketView, ConfirmToken, ContactView, LoginAccount, OrderView, PartnerUpdate, ProductInfoView, RegisterAccount

app_name = 'backend'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmToken.as_view(), name='user-register-confirm'),
    path('products', ProductInfoView.as_view(), name='shops'),
    path('basket', BasketView.as_view(), name='basket'),
    path('contact', ContactView.as_view(), name='contact'),
    path('order', OrderView.as_view(), name='order')
]