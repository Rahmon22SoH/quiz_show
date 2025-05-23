from dotenv import load_dotenv
import os
from datetime import timedelta
from celery.schedules import crontab
# Определяем окружение
APP_ENV = os.getenv('APP_ENV', 'local')

# Для локального окружения явно загружаем .env
if APP_ENV == 'local':
	load_dotenv('.env')
else:
	# В Docker переменные окружения уже подставляются, .env не нужен
	pass

basedir = os.path.abspath(os.path.dirname(__file__))

# Добавляем константу для московского времени (UTC+3)
MOSCOW_UTC_OFFSET = timedelta(hours=3)
MOSCOW_TIMEZONE = MOSCOW_UTC_OFFSET

class Config:
	# Здесь настраиваем параметры для отправки писем через SMTP-сервер Google
	MAIL_SERVER  = 'smtp.gmail.com'
	MAIL_PORT = 587
	MAIL_USE_TLS= True
	MAIL_USERNAME = os.getenv('MAIL_USERNAME')
	MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
	ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
	ADMIN_PASSWORD = os.getenv('PASSWORD_ADMIN')
	FLASKY_MAIL_SUBJECT_PREFIX  = '[Flasky]'
	FLASKY_MAIL_SENDER  = 'Flasky Admin <mebelnazakazms@gmail.com>'
	FLASKY_ADMIN  = os.getenv('FLASKY_ADMIN')
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
	SQLALCHEMY_COMMIT_ON_TEARDOWN = True
	SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	WTF_CSRF_ENABLED = True
	WTF_CSRF_TIME_LIMIT = 3600
	WTF_CSRF_SSL_STRICT = True
	CSRF_TRUSTED_ORIGINS = ['https://quizz-show-app.loca.lt']
	
	# Настройки сессии
	SESSION_TYPE = 'filesystem'
	PERMANENT_SESSION_LIFETIME = timedelta(days=30)
	PREFERRED_URL_SCHEME = 'https'
	SESSION_COOKIE_NAME = 'quiz_session'
	SESSION_COOKIE_SECURE = False  # Для тестов через HTTPS/туннель
	SESSION_COOKIE_HTTPONLY = True
	SESSION_COOKIE_SAMESITE = 'Lax'
	
	# Настройки Flask-Login
	REMEMBER_COOKIE_DURATION = timedelta(days=30)
	REMEMBER_COOKIE_SECURE = False  # Для тестов через HTTPS/туннель
	REMEMBER_COOKIE_HTTPONLY = True
	REMEMBER_COOKIE_NAME = 'remember_token'
	
	# Настройки SQLAlchemy
	if APP_ENV == 'local':
		SQLALCHEMY_ENGINE_OPTIONS = {
			'pool_pre_ping': True,
			'pool_recycle': 300,
			'pool_size': 5,        # Маленький пул для локального запуска
			'max_overflow': 10,    # Дополнительные соединения при пике
			'pool_timeout': 30,
		}
	else:
		SQLALCHEMY_ENGINE_OPTIONS = {
			'pool_pre_ping': True,
			'pool_recycle': 300,
			'pool_size': 50,        # Основной пул соединений для Docker
			'max_overflow': 100,    # Дополнительные соединения при пике
			'pool_timeout': 30,
		}

	# Настройки Telegram
	TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
	TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME')
	TELEGRAM_LOGIN_REDIRECT_URL = os.getenv('TELEGRAM_LOGIN_REDIRECT_URL', 'http://quiz-show-app.loca.lt/auth/telegram/callback')
	TELEGRAM_AUTH_EXPIRATION = 86400  # 24 часа
	
	# Webhook URL будет использоваться только в production
	TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')

	broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
	result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
	accept_content = ['json']
	task_serializer = 'json'
	result_serializer = 'json'
	timezone = 'Europe/Moscow'
	enable_utc = False
	imports = ('app.celery.tasks',)
	beat_schedule = {
		'check-quiz-expiration': {
			'task': 'app.celery.tasks.check_quiz_expiration',
			'schedule': crontab(minute='*')
		}
	}
	beat_max_loop_interval = 60 # установить максимальный интервал в 1 минуту

	# Настройки профилирования для проверки ручек
	ENABLE_PROFILING = os.getenv('ENABLE_PROFILING', 'False').lower() == 'true'
	DEBUG_TB_ENABLED = ENABLE_PROFILING
	DEBUG_TB_INTERCEPT_REDIRECTS = False
	DEBUG_TB_PROFILER_ENABLED = True
	DEBUG_TB_TEMPLATE_EDITOR_ENABLED = True
	
	# Настройки логирования
	LOG_TO_STDOUT = False
	SQLALCHEMY_ECHO = False  # Отключаем вывод SQL в консоль
	SQLALCHEMY_RECORD_QUERIES = True  # Включаем запись SQL запросов для профилирования

	# Настройки кэширования
	CACHE_TYPE = "redis"
	CACHE_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
	CACHE_DEFAULT_TIMEOUT = 300  # Время жизни кэша по умолчанию (5 минут)

	# Дополнительные настройки безопасности
	SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT', 'your-salt-here')
	SECURITY_PASSWORD_HASH = 'bcrypt'
	JSON_AS_ASCII = False  # Поддержка Unicode в JSON подумать над этим возможно пользователи не будут видеть кириллицу
	MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Ограничение размера загружаемых файлов (16MB)

	@classmethod
	def init_app(cls, app):
		# Логируем строку подключения к БД
		app.logger.info(f"SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
		# Проверяем обязательные настройки Telegram
		if not app.config.get('TELEGRAM_BOT_TOKEN'):
			app.logger.warning('TELEGRAM_BOT_TOKEN is not set')
		if not app.config.get('TELEGRAM_BOT_USERNAME'):
			app.logger.warning('TELEGRAM_BOT_USERNAME is not set')
		# Явно добавляем celery параметры в app.config
		app.config['broker_url'] = cls.broker_url
		app.config['result_backend'] = cls.result_backend
		app.config['accept_content'] = cls.accept_content
		app.config['task_serializer'] = cls.task_serializer
		app.config['result_serializer'] = cls.result_serializer
		app.config['timezone'] = cls.timezone
		app.config['enable_utc'] = cls.enable_utc
		app.config['imports'] = cls.imports
		app.config['beat_schedule'] = cls.beat_schedule
		app.config['beat_max_loop_interval'] = cls.beat_max_loop_interval

class DevelopmentConfig(Config):
	DEBUG = True

class TestingConfig(Config):
	TESTING = True

class ProductionConfig(Config):
	pass

# Словарь конфигураций
config = {
	'development': DevelopmentConfig,
	'testing': TestingConfig,
	'production': ProductionConfig,
	'default': DevelopmentConfig
}

	