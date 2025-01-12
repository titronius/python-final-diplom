# Дипломный проект профессии «Python-разработчик: расширенный курс»

## Backend-приложение для автоматизации закупок

Реализация ТЗ по [дипломной работе Нетологии](https://github.com/netology-code/python-final-diplom)

Приложение работает на стэке DJANGO, CELERY, REDIS.

## Docker-compose
Приложение докеризировано, для запуска контейнера используем команды оркестратора:

```
docker-compose up -d
```

Django сервер запускается на порту 1337, точка входа:
http://localhost:1337/

## Примеры запросов:
Файл [request-examples.http](./request-examples.http)