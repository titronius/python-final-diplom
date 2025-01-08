from django.urls import path
from backend.views import BasketView, ConfirmToken, ContactView,\
LoginAccount, OrderView, PartnerOrders, PartnerState, PartnerUpdate, ProductInfoView, RegisterAccount

from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

app_name = 'backend'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmToken.as_view(), name='user-register-confirm'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('products', ProductInfoView.as_view(), name='shops'),
    path('basket', BasketView.as_view(), name='basket'),
    path('contact', ContactView.as_view(), name='contact'),
    path('order', OrderView.as_view(), name='order')
]