# Дипломный проект профессии «Python-разработчик: расширенный курс»

## Backend-приложение для автоматизации закупок

Реализация ТЗ по [дипломной работе Нетологии](https://github.com/netology-code/python-final-diplom)

Приложение работает на стэке DJANGO, CELERY, REDIS.

## Docker-compose
Для работы приложения необходимо создать в корне .env файл с переменными виртуального окружения:

```
ADMIN_EMAIL = 'admin@gmail.com' # адрес почты админа для информирования о новых заказах
EMAIL_HOST_USER = 'mail@mail.ru' # адрес почты SMTP сервера
EMAIL_HOST_PASSWORD = 'password' # пароль почты SMTP сервера Инструкция для получения: https://help.mail.ru/mail/security/protection/external/
EMAIL_PORT = '465'
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_WORKER_RUNNING = 'True'

# Следующие переменные для полученяи токена при помощи соц.сети, а именно google. Тут инструкция, как получить эти переменные: https://developers.google.com/identity/protocols/oauth2?hl=ru
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = 'GOOGLE_OAUTH2_KEY'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'GOOGLE_OAUTH2_SECRET'

# Токее приложения дял трэйсинга ошибок, получать тут: https://rollbar.com/
ROLLBAR_ACCESS_TOKEN = 'ROLLBAR_ACCESS_TOKEN'
```

Приложение докеризировано, для запуска контейнера используем команды оркестратора:

```
docker-compose up -d # Запуск приложения
docker-compose up test # Запуск тестов и вывод информации о покрытии
```

Django сервер запускается на порту 1337, точка входа:
http://localhost:1337/

## Документация SWAGGER
Документация формируется благодаря drf_spectacular и прописанию схемы в [schema.py](orders/backend/schema.py)

Ссылка на сервере:
http://localhost:1337/api/docs/


## Авторизация через соц. сети
Авторизовавшись через google - можно получить токен.

http://localhost:1337/social/login/google-oauth2/

## Примеры запросов:
Файл [request-examples.http](./request-examples.http)