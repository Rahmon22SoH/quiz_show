from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_login import LoginManager
from datetime import timedelta
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect # (Убрать после тестов CSRFProtect)


# Создаем экземпляры расширений *без* привязки к приложению.
db = SQLAlchemy()
cache = Cache()
migrate = Migrate()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://127.0.0.1:6379/0")
login_manager = LoginManager()
login_manager.session_protection = 'strong' # None # 'strong' поменять на 'strong'
login_manager.login_view = 'auth.login'  # Указываем view для входа
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'
login_manager.remember_cookie_duration = timedelta(days=30)
login_manager.refresh_view = 'auth.login'  # Указываем view для обновления сессии
login_manager.needs_refresh_message = 'Пожалуйста, войдите заново для подтверждения доступа.'
login_manager.needs_refresh_message_category = 'info'

csrf = CSRFProtect() # (Убрать после тестов CSRFProtect)