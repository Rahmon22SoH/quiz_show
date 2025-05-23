from flask_login import UserMixin
from datetime import datetime
from flask import url_for
from app.extensions import db
from app.models.base import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash # --- Методы для работы с password_hash паролем для тестов удалить на проде  ---
from decimal import Decimal
from sqlalchemy import Numeric

class User(UserMixin, BaseModel):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(64), unique=True, index=True)
    # --- Методы для работы с password_hash паролем для тестов удалить на проде  ---
    password_hash = db.Column(db.String(128), nullable=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Integer, default=0)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    # Telegram fields
    telegram_id = db.Column(db.String(128), unique=True, nullable=False)
    telegram_username = db.Column(db.String(64), nullable=True)
    telegram_auth_date = db.Column(db.DateTime, nullable=False)
    telegram_photo_url = db.Column(db.String(255), nullable=True)
    telegram_link = db.Column(db.String(255), nullable=True)

    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)

    donation_balance = db.Column(Numeric(precision=12, scale=2), default=Decimal('0.00'))  # Сумма донатов через DonationAlerts (USD)

     # Индексы для оптимизации запросов
    __table_args__ = (
        db.Index('idx_user_username', 'username'),
        db.Index('idx_user_telegram_id', 'telegram_id'),
    )
    
    notification_logs = db.relationship('NotificationLog', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def is_active(self):
        """Проверка активности пользователя"""
        return self.active and not self.is_locked

    @property
    def is_blocked(self):
        """Проверка блокировки пользователя"""
        return not self.active or self.is_locked

    def activate(self):
        """Активация пользователя"""
        self.active = True
        self.is_locked = False
        return self.save()

    def deactivate(self):
        """Деактивация пользователя"""
        self.active = False
        return self.save()

    def lock(self):
        """Блокировка пользователя"""
        self.is_locked = True
        return self.save()

    def unlock(self):
        """Разблокировка пользователя"""
        self.is_locked = False
        return self.save()

    def block(self):
        """Полная блокировка пользователя"""
        self.active = False
        self.is_locked = True
        return self.save()

    def unblock(self):
        """Полная разблокировка пользователя"""
        self.active = True
        self.is_locked = False
        return self.save()

    @classmethod
    def get_or_create_from_telegram(cls, telegram_data, telegram_link=None):
        """Получает или создает пользователя на основе данных из Telegram."""
        from app.models.role import Role  # Импорт здесь для избежания циклических зависимостей
        
        try:
            print(f"Processing Telegram data: {telegram_data}")
            user = cls.query.filter_by(telegram_id=str(telegram_data['telegram_id'])).first()
            
            if user is None:
                default_role = Role.query.filter_by(name='user').first()
                if not default_role:
                    print("Error: role 'user' not found")
                    raise Exception("Default role 'user' not found")

                username = telegram_data.get('username') or f"user_{telegram_data['telegram_id']}"
                
                # Проверяем уникальность username
                base_username = username
                counter = 1
                while cls.query.filter_by(username=username).first() is not None:
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = cls(
                    telegram_id=str(telegram_data['telegram_id']),
                    telegram_username=telegram_data.get('username'),
                    username=username,
                    first_name=telegram_data['first_name'],
                    last_name=telegram_data.get('last_name', ''),
                    telegram_photo_url=telegram_data.get('photo_url'),
                    telegram_auth_date=datetime.fromtimestamp(int(telegram_data['auth_date'])),
                    telegram_link=telegram_link,  # Сохраняем ссылку на профиль Telegram
                    phone=telegram_data.get('phone'),  # Сохраняем телефон, если есть
                    role_id=default_role.id,
                    active=True
                )
                if not user.save():
                    raise Exception("Failed to save new user")
            else:
                # Обновляем существующего пользователя
                user.telegram_username = telegram_data.get('username')
                user.telegram_photo_url = telegram_data.get('photo_url')
                user.telegram_auth_date = datetime.fromtimestamp(int(telegram_data['auth_date']))
                user.first_name = telegram_data['first_name']
                user.last_name = telegram_data.get('last_name', user.last_name)
                user.telegram_link = telegram_link  # Обновляем ссылку на профиль Telegram
                user.phone = telegram_data.get('phone', user.phone)  # Обновляем телефон, если есть
                user.active = True
                if not user.save():
                    raise Exception("Failed to update user")
            
            return user
        except Exception as e:
            print(f"Error in get_or_create_from_telegram: {str(e)}")
            db.session.rollback()
            raise

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        """Возвращает уникальный идентификатор пользователя (ID)."""
        return str(self.id)

    @property
    def is_admin(self):
        """Проверяет, является ли пользователь администратором."""
        return self.role and self.role.name == 'admin'
    
    def get_redirect_url(self):
        """Возвращает URL для редиректа после входа."""
        if self.is_admin:
            return url_for('admin.dashboard')
        return url_for('main.index')

    # --- Методы для работы с паролем для тестов удалить на проде  ---
    def set_password(self, password):
        """Устанавливает хеш пароля."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет соответствие пароля хешу."""
        if not self.password_hash:
            return False # Если хеша нет, пароль не может совпасть
        return check_password_hash(self.password_hash, password)
    # --- 