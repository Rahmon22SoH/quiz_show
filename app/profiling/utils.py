import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging
import os
import sys  # Добавлено для stdout
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # Добавляем user_id, quiz_id если они есть в extra
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        if hasattr(record, "quiz_id"):
            log_record["quiz_id"] = record.quiz_id
        return json.dumps(log_record, ensure_ascii=False)

def init_profiling_logger():
    base_logger = logging.getLogger('app.profiling')
    base_logger.setLevel(logging.INFO)
    # Используем StreamHandler для stdout вместо FileHandler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    base_logger.handlers = []
    base_logger.addHandler(stream_handler)
    return base_logger

def setup_db_profiling():
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.INFO)
    sql_logger.handlers = []
    # Используем StreamHandler для stdout вместо FileHandler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    sql_logger.addHandler(stream_handler)
    sql_logger.propagate = False

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        sql_logger.info(f"Query execution time: {total:.4f}s", extra={})
        sql_logger.info(f"Query: {statement}", extra={})
        sql_logger.info(f"Parameters: {parameters}", extra={})

def setup_logging():
    # Инициализируем базовый логгер для профилирования
    base_logger = init_profiling_logger()
    
    # Настраиваем логгер для view функций
    view_logger = logging.getLogger('app.profiling.views')
    view_logger.setLevel(logging.INFO)
    view_logger.parent = base_logger
    
    # Настраиваем логгер для celery задач
    celery_logger = logging.getLogger('app.profiling.celery')
    celery_logger.setLevel(logging.INFO)
    celery_logger.parent = base_logger
    
    return base_logger