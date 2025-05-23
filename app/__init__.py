from flask import Flask, request
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from app.extensions import db, login_manager, mail, moment, bootstrap, migrate, cache, csrf, limiter # (Убрать после тестов csrf)
from .celery import celery, init_celery
from app.main import main as main_blueprint
from app.auth import auth as auth_blueprint
from app.admin import admin as admin_blueprint
from app.quiz import quiz as quiz_blueprint
from app.profile import profile as profile_blueprint
from app.auth.auth_utils import seed_roles_and_admin
from app.models import QuizSession
from app.profiling import init_profiling, setup_db_profiling, setup_logging
from datetime import timedelta
from app.utils.error_handlers import init_error_handlers
from app.utils.logger import setup_logger
from config import config
import os
import logging
from flask_caching import Cache
from flask import session
from flask_login import current_user

def create_app(config_name='default'):
    """
    Фабрика приложений.  Создает и настраивает экземпляр приложения Flask.

    Args:
        config_name (str): Имя конфигурации (development, production, testing).

    Returns:
        Flask: Экземпляр приложения Flask.
    """
    app = Flask(__name__)
    app.logger.info('START: create_app')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    app.logger.info('Config loaded')
    
    # Настройка базового логгера
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    app.logger.info('Base logger set')
    
    # Инициализация профилирования
    if app.config.get('ENABLE_PROFILING', False):
        app_logger.info("Initializing profiling...")
        init_profiling(app)
        setup_db_profiling()
        base_logger = setup_logging()
        
        # Активируем запись SQL-запросов для мониторинга
        app.config['SQLALCHEMY_RECORD_QUERIES'] = True
        app_logger.info("SQL query recording enabled")
        
        app_logger.info("Profiling initialized successfully")
    app.logger.info('Profiling checked')
    
    # Настройки безопасности
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        
        # Content Security Policy (CSP) — настройка безопасности для браузера
        # Каждая директива снабжена поясняющим комментарием
        script_src = "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://telegram.org https://cdnjs.cloudflare.com https://www.google-analytics.com"
        if app.debug:
            # В режиме разработки разрешаем 'unsafe-eval' для дебаг-панели
            script_src += " 'unsafe-eval'"
        csp = (
            # Разрешаем загрузку контента только с текущего домена
            "default-src 'self';"
            # Разрешаем выполнение скриптов только с указанных источников
            f"script-src {script_src};"
            # Разрешаем стили только с указанных источников
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;"
            # Разрешаем изображения с текущего домена, data: (base64), blob: и Telegram
            "img-src 'self' data: https: blob: https://telegram.org https://*.telegram.org;"
            # Разрешаем шрифты только с CDN и data:
            "font-src 'self' https://cdnjs.cloudflare.com data:;"
            # Разрешаем соединения только с self, Telegram и localtunnel
            "connect-src 'self' https://quizz-show-app.loca.lt https://telegram.org https://*.telegram.org wss://*.telegram.org;"
            # Разрешаем фреймы только с self и Telegram
            "frame-src 'self' https://telegram.org https://*.telegram.org;"
            # Разрешаем медиа только с self
            "media-src 'self';"
            # Запрещаем плагины (object, embed)
            "object-src 'none';"
            # Ограничиваем base URI
            "base-uri 'self';"
            # Разрешаем отправку форм только на self и Telegram
            "form-action 'self' https://telegram.org;"
            # Разрешаем встраивание только в Telegram и self
            "frame-ancestors 'self' https://telegram.org;"
            # Принудительно используем HTTPS для всех запросов
            "upgrade-insecure-requests;"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Добавляем дополнительные заголовки безопасности
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        #response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        #response.headers['Cross-Origin-Resource-Policy'] = 'same-site'
        #response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # Настройка CORS для localtunnel
        if request.headers.get('Origin'):
            allowed_origins = ['https://quizz-show-app.loca.lt']
            if request.headers['Origin'] in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH,OPTIONS' 
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, X-Requested-With'
        
        return response
    app.logger.info('Security headers set')
    
    # Настройки сессии и CSRF
    app.config.update(
        # SESSION_COOKIE_SECURE=True, # <-- Закомментировано, берем из config.py
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_TYPE='filesystem',
        # REMEMBER_COOKIE_SECURE=True, # <-- Закомментировано, берем из config.py
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_DURATION=timedelta(days=30),
        REMEMBER_COOKIE_NAME='remember_token',
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,
        WTF_CSRF_SSL_STRICT=True,  # Включаем строгую проверку SSL
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_METHODS=['POST', 'PUT', 'PATCH', 'DELETE']
    )
    app.logger.info('Session and CSRF config set')
    
    # Отладка CSRF
    # @app.before_request
    # def csrf_debug():
    #     app.logger.info('before_request: csrf_debug called')
    #     if request.method == "POST":
    #         app.logger.info(f"CSRF Debug - Headers: {dict(request.headers)}")
    #         app.logger.info(f"CSRF Debug - Form Data: {request.form}")
    #         app.logger.info(f"CSRF Debug - Cookies: {request.cookies}")
    # app.logger.info('CSRF debug set')
    
    # Логирование каждого запроса
    # @app.before_request
    # def log_request_info():
    #     app.logger.info('before_request: log_request_info called')
    #     app.logger.info(f'Request: {request.method} {request.path} from {request.remote_addr}')
    # app.logger.info('Request logging set')
    
    # Инициализация расширений
    app.logger.info('START: extensions init')
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    app.logger.info('END: extensions init')
    
    # Инициализация Celery
    init_celery(app)
    app.logger.info('Celery initialized')

    # Настройка логирования
    app.logger.info('START: setup_logger')
    try:
        setup_logger(app)
        app.logger.info('END: setup_logger')
    except Exception as e:
        print(f"Error initializing logger (возможно, таблицы logs ещё нет): {e}")
        app.logger.error(f"Error initializing logger: {e}")
    
    # Регистрация blueprints
    app.logger.info('START: register blueprints')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(quiz_blueprint, url_prefix='/quiz')
    app.register_blueprint(profile_blueprint, url_prefix='/profile')
    app.logger.info('END: register blueprints')

    # Инициализация обработчиков ошибок
    app.logger.info('START: error handlers')
    init_error_handlers(app)
    app.logger.info('END: error handlers')

    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')

    # ВРЕМЕННОЕ ЛОГИРОВАНИЕ для диагностики проблем сессии и авторизации
    # @app.before_request
    # def debug_session():
    #     app.logger.info(f"Session: {dict(session)}")
    #     app.logger.info(f"Current user: {current_user.get_id() if current_user.is_authenticated else 'Anonymous'}")

    app.logger.info('END: create_app')
    return app
