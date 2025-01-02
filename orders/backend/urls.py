from django.urls import path
from backend.views import LoginAccount, PartnerUpdate

app_name = 'backend'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
]