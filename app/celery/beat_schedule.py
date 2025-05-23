from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'check-quiz-expiration': {
        'task': 'app.celery.tasks.check_quiz_expiration',
        'schedule': crontab(minute='*')  # Запускать каждую минуту
    },
    'cleanup-old-logs': {
        'task': 'app.celery.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 03:00 ночи
    }
}
