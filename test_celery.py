from app import create_app, celery
from app.celery.tasks import test_task

# Создаем контекст приложения
app = create_app()
app.app_context().push()

if __name__ == '__main__':
    print("Starting test task...")
    result = test_task.delay()
    print(f"Task ID: {result.id}")
    print("Check your Celery worker console for results!")