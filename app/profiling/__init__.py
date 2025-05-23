from .utils import setup_db_profiling, setup_logging
from .decorators import profile_view, profile_celery_task

__all__ = [
    'init_profiling',
    'setup_db_profiling',
    'setup_logging',
    'profile_view',
    'profile_celery_task'
]

def init_profiling(app):
    """Инициализация профилирования"""
    # Настраиваем перехват редиректов (оставляем полезную настройку)
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True