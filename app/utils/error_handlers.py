from flask import render_template, jsonify, request
from app.extensions import db
from app.utils.action_logger import log_action
import traceback
import logging

# Настройка логгера
logger = logging.getLogger(__name__)
handler = logging.FileHandler('error.log')
handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def handle_error(error, status_code=500):
    """Централизованная обработка ошибок."""
    error_details = {
        'error': str(error),
        'path': request.path,
        'method': request.method,
        'status_code': status_code
    }
    
    # Логируем ошибку
    logger.error(f"Error: {error_details}\nTraceback: {traceback.format_exc()}")
    
    # Логируем в базу данных
    try:
        log_action('Error', 
                  details=f"Path: {request.path}, Error: {str(error)}")
    except Exception as e:
        logger.error(f"Failed to log error to database: {str(e)}")
    
    # Проверяем, является ли запрос AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(error_details), status_code
        
    # Иначе рендерим страницу с ошибкой
    return render_template('errors/error.html', 
                         error=error_details), status_code

def init_error_handlers(app):
    """Инициализация обработчиков ошибок."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return handle_error(error, 404)

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return handle_error(error, 500)

    @app.errorhandler(403)
    def forbidden_error(error):
        return handle_error(error, 403)

    @app.errorhandler(401)
    def unauthorized_error(error):
        return handle_error(error, 401)

    @app.errorhandler(429)
    def ratelimit_error(error):
        # Передаем дружелюбное сообщение для 429
        return handle_error("Слишком много запросов. Пожалуйста, попробуйте позже.", 429) 