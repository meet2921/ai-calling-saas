from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

CAMPAIGN_BROKER_URL = os.getenv("CAMPAIGN_BROKER_URL")
CAMPAIGN_RESULT_BACKEND = os.getenv("CAMPAIGN_RESULT_BACKEND")

celery_app = Celery(
    "campaign_worker",
    broker=CAMPAIGN_BROKER_URL,
    backend=CAMPAIGN_RESULT_BACKEND,
)

celery_app.autodiscover_tasks(["app.tasks.campaign_tasks", "app.tasks.scheduled_tasks"])

celery_app.conf.task_routes = {
    "app.tasks.campaign_tasks.process_campaign": {
        "queue": "campaign_queue",
    },
}

celery_app.conf.broker_connection_retry_on_startup = True

# Beat schedule — check for due scheduled campaigns every minute
celery_app.conf.beat_schedule = {
    "trigger-scheduled-campaigns": {
        "task": "app.tasks.scheduled_tasks.trigger_scheduled_campaigns",
        "schedule": 60.0,  # seconds
    },
    "auto-complete-stale-campaigns": {
        "task": "app.tasks.scheduled_tasks.auto_complete_stale_campaigns",
        "schedule": 60.0,  # seconds
    },
}