import time
from functools import wraps
import logging
import cProfile
import pstats
from io import StringIO
import threading

# Используем правильные пространства имен для логгеров
celery_logger = logging.getLogger('app.profiling.celery')
view_logger = logging.getLogger('app.profiling.views')

# Добавляем локальное хранилище для отслеживания состояния профайлера
_profiler_context = threading.local()

def profile_celery_task(task_func):
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = task_func(*args, **kwargs)
            duration = time.time() - start_time
            celery_logger.info(
                f"Task {task_func.__name__} completed in {duration:.4f}s",
                extra={"task_name": task_func.__name__}
            )
            return result
        except Exception as e:
            celery_logger.error(
                f"Task {task_func.__name__} failed: {str(e)}",
                extra={"task_name": task_func.__name__}
            )
            raise
    return wrapper

def profile_view(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # Проверяем, не активен ли уже профайлер
        if hasattr(_profiler_context, 'active') and _profiler_context.active:
            view_logger.warning(
                f"Profiler is already active for {view_func.__name__}, skipping profiling",
                extra={"view_name": view_func.__name__}
            )
            return view_func(*args, **kwargs)

        pr = cProfile.Profile()
        start_time = time.time()
        _profiler_context.active = True
        
        try:
            pr.enable()
            result = view_func(*args, **kwargs)
            pr.disable()
            
            duration = time.time() - start_time
            
            # Формируем отчет профилирования
            s = StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats(30)  # Ограничиваем вывод 30 самыми важными строками
            
            view_logger.info(
                f"View {view_func.__name__} completed in {duration:.4f}s",
                extra={"view_name": view_func.__name__}
            )
            view_logger.info(
                f"Profile for {view_func.__name__}:\n{s.getvalue()}",
                extra={"view_name": view_func.__name__}
            )
            
            return result
            
        except Exception as e:
            view_logger.error(
                f"View {view_func.__name__} failed: {str(e)}",
                extra={"view_name": view_func.__name__}
            )
            raise
            
        finally:
            # Гарантированно отключаем профайлер и очищаем флаг
            if hasattr(pr, 'disable'):
                pr.disable()
            _profiler_context.active = False
            
    return wrapper