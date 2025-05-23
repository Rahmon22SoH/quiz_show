from app import create_app
from app.celery import celery, init_celery

flask_app = create_app()
init_celery(flask_app)

# Импорт задач после инициализации celery и app!
import app.celery.tasks

flask_app.app_context().push()
print("BROKER:", celery.conf.broker_url)
print("BACKEND:", celery.conf.result_backend)