from rest_framework.authtoken.models import Token
from django.http import JsonResponse

def get_token_google_oauth(user=None, *args, **kwargs):
    """
    The function is used to get the token for the user who was authenticated by Google OAuth2
    
    Parameters:
    - strategy (str): The name of the strategy used for authentication
    - details (dict): The result of the authentication process
    - user (User): The user object
    - *args (list): Additional arguments
    - **kwargs (dict): Additional keyword arguments
    
    Returns:
    - JsonResponse: The response containing the token or an error message
    """
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return JsonResponse({'Status': True, 'Token': token.key})
    else:
        return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'}, json_dumps_params={'ensure_ascii': False})