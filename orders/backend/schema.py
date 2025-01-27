from rest_framework import serializers

class BaseResponse(serializers.Serializer):
    Status = serializers.BooleanField()

class RegisterAccountRequest(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    company = serializers.CharField(required=False)
    position = serializers.CharField(required=False)
    avatar = serializers.URLField(required=False)
    
class RegisterAccountResponse(BaseResponse):
    pass
    
class LoginAccountRequest(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class LoginAccountResponse(serializers.Serializer):
    Status = serializers.BooleanField()
    Token = serializers.CharField()

class PartnerUpdateRequest(serializers.Serializer):
    url = serializers.URLField()
    
class PartnerUpdateResponse(BaseResponse):
    pass

class PartnerStateRequest(serializers.Serializer):
    state = serializers.CharField(default='True')

class PartnerStateResponse(BaseResponse):
    pass

class BasketBaseRequest(serializers.Serializer):
    product_info = serializers.IntegerField()

class BasketAddUpdateRequest(BasketBaseRequest):
    quantity = serializers.IntegerField()
    
class BasketAddResponse(BaseResponse):
    objects_created = serializers.IntegerField()

class BasketDeleteResponse(BaseResponse):
    objects_deleted = serializers.IntegerField()

class BasketUpdateResponse(BaseResponse):
    objects_updated = serializers.IntegerField()
    
class ContactRequest(serializers.Serializer):
    city = serializers.CharField()
    street = serializers.CharField()
    house = serializers.CharField()
    structure = serializers.CharField(required=False)
    building = serializers.CharField(required=False)
    apartment = serializers.CharField(required=False)
    phone = serializers.CharField()

class ContactResponse(BaseResponse):
    pass

class OrderConfirmRequest(serializers.Serializer):
    contact_id = serializers.IntegerField()
    order_id = serializers.IntegerField()

class OrderResponse(BaseResponse):
    pass

class OrderUpdateRequest(serializers.Serializer):
    order_id = serializers.IntegerField()
    state = serializers.CharField()