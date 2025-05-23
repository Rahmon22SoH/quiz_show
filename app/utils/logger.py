import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from flask import request, current_app
from datetime import datetime
import time


def setup_logger(app):
    """Настройка логирования для приложения."""
    # директорию для логов 
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Путь к файлу лога
    log_file = os.path.join(log_dir, 'app.log')
    
    # Используем RotatingFileHandler для ротации по размеру
    # Максимальный размер файла - 10 МБ, хранить до 10 файлов
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=10,
        encoding='utf-8'
    )

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Добавляем обработчик только если его еще нет
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == file_handler.baseFilename for h in app.logger.handlers):
        app.logger.addHandler(file_handler)
    
    # Добавляем обработчик ошибок
    def handle_error(exc_info):
        if isinstance(exc_info[1], PermissionError):
            time.sleep(1)  # Ждем 1 секунду перед повторной попыткой
            return True  # Повторить попытку
        return False
    
    file_handler.handleError = handle_error
    
    # Устанавливаем уровень логирования для всех логов
    app.logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие обработчики
    app.logger.handlers = []
    
    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
    
    # Добавляем обработчик для записи логов в базу данных
    class DatabaseHandler(logging.Handler):
        def emit(self, record):
            from app.models import Log
            from app.extensions import db
            
            try:
                # Создаем запись в базе данных
                log_entry = Log(
                    level=record.levelname,
                    message=record.getMessage(),
                    module=record.module,
                    function=record.funcName,
                    line=record.lineno
                )
                
                # Сохраняем в базе данных
                with app.app_context():
                    db.session.add(log_entry)
                    db.session.commit()
            except Exception as e:
                # Избегаем рекурсивного логирования
                print(f"Error saving log to database: {str(e)}")
    
    # Добавляем обработчик для базы данных со всеми уровнями логирования
    db_handler = DatabaseHandler()
    db_handler.setLevel(logging.DEBUG)  # Логируем все уровни
    app.logger.addHandler(db_handler)
    
    app.logger.info('Quiz Show startup')


def log_info(message, category='INFO'):
    """Логирование информационных сообщений."""
    try:
        current_app.logger.info(f'{category}: {message}')
    except Exception as e:
        print(f"Failed to log info: {str(e)}")


def log_error(message, category='ERROR'):
    """Логирование ошибок."""
    try:
        current_app.logger.error(f'{category}: {message}')
    except Exception as e:
        print(f"Failed to log error: {str(e)}")


def log_warning(message, category='WARNING'):
    """Логирование предупреждений."""
    try:
        current_app.logger.warning(f'{category}: {message}')
    except Exception as e:
        print(f"Failed to log warning: {str(e)}")


def log_debug(message, category='DEBUG'):
    """Логирование отладочной информации."""
    try:
        current_app.logger.debug(f'{category}: {message}')
    except Exception as e:
        print(f"Failed to log debug: {str(e)}")

def log_request():
    """Логирование запросов."""
    try:
        # Не логируем check-auth запросы
        if request.path != '/auth/check-auth':
            current_app.logger.info(f'Request: {request.method} {request.path} from {request.remote_addr}')
    except Exception as e:
        print(f"Failed to log request: {str(e)}")

def log_event(action, user_id=None, details=None, level="INFO", message=None, module=None, function=None, line=None):
    """
    Запись бизнес-события в таблицу Log.
    """
    from app.models import Log
    from app.extensions import db

    log = Log(
        user_id=user_id,
        action=action,
        details=details,
        level=level,
        message=message,
        module=module,
        function=function,
        line=line
    )
    db.session.add(log)
    db.session.commit()

def make_details(**kwargs):
    """
    Генерирует строку details для логирования бизнес-событий.
    Пример: make_details(user_id=5, username='vasya', ip='1.2.3.4', quiz_id=7)
    -> "user_id=5, username=vasya, ip=1.2.3.4, quiz_id=7"
    """
    return ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None) 