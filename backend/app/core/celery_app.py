from celery import Celery

celery_app = Celery(
    "campaign_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.task_routes = {
    "app.tasks.campaign_tasks.process_campaign": {
        "queue": "campaign_queue",
    },
}