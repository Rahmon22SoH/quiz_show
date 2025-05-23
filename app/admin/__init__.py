from flask import Blueprint, request, current_app
import time

admin = Blueprint('admin', __name__)

# Логирование времени обработки каждого запроса в admin blueprint
@admin.before_request
def admin_start_timer():
    request._admin_start_time = time.time()

@admin.after_request
def admin_log_request_time(response):
    if hasattr(request, '_admin_start_time'):
        duration = time.time() - request._admin_start_time
        current_app.logger.info(f"[admin] {request.method} {request.path} took {duration:.2f} seconds")
    return response

# Импортируем views *после* создания объекта Blueprint.
from app.admin import views