# Дипломный проект профессии «Python-разработчик: расширенный курс»

## Backend-приложение для автоматизации закупок

Реализация ТЗ по [дипломной работе Нетологии](https://github.com/netology-code/python-final-diplom)

Приложение работает на стэке DJANGO, CELERY, REDIS.

## Docker-compose
Для работы приложения необходимо создать в корне .env файл с перменными виртуального окружения:

```
ADMIN_EMAIL = 'admin@gmail.com' # адрес почты админа для информирования о новых заказах
EMAIL_HOST_USER = 'mail@mail.ru' # адрес почты SMTP сервера
EMAIL_HOST_PASSWORD = 'fa2zb7NuggRwzUFLyVhX' # пароль почты SMTP сервера Инструкция для получения: https://help.mail.ru/mail/security/protection/external/
EMAIL_PORT = '465'
CELERY_BROKER_URL = 'redis://redis:6379/0'
```

Приложение докеризировано, для запуска контейнера используем команды оркестратора:

```
docker-compose up -d
```

Django сервер запускается на порту 1337, точка входа:
http://localhost:1337/

## Примеры запросов:
Файл [request-examples.http](./request-examples.http)