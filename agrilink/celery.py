import os
from celery import Celery

# Set default Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agrilink.settings")

app = Celery("agrilink")

# Load task modules from all registered Django app configs
app.config_from_object("django.conf:settings", namespace="CELERY")

# Ensure Celery retries broker connections on startup (useful for distributed systems)
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_max_retries = None

# Enable task result expiration (clean old results)
app.conf.result_expires = 3600  # 1 hour, adjust based on your needs

# Ensure tasks are not lost
app.conf.task_acks_late = True  # Ensures tasks are acknowledged only after execution
app.conf.task_reject_on_worker_lost = True  # Prevents tasks from being lost if worker crashes

app.autodiscover_tasks()

# Enable logging for Celery
app.conf.worker_hijack_root_logger = False
app.conf.task_send_sent_event = True

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
