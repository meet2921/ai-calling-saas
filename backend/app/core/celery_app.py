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

celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.task_routes = {
    "app.tasks.campaign_tasks.process_campaign": {
        "queue": "campaign_queue",
    },
}