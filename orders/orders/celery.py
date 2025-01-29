from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import task_failure
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')

app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

if bool(os.environ.get('CELERY_WORKER_RUNNING', False)):
    import rollbar
    rollbar.init(**settings.ROLLBAR)

    def celery_base_data_hook(request, data):
        data['framework'] = 'celery'

    rollbar.BASE_DATA_HOOK = celery_base_data_hook

    @task_failure.connect
    def handle_task_failure(**kw):
        rollbar.report_exc_info(extra_data=kw)