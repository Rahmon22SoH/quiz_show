from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db
import secrets

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role')

    def __repr__(self):
        return f'<Role {self.name}>'
    
    
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    # last_login_at = db.Column(db.DateTime, nullable=True) # Время последнего входа
    salt = db.Column(db.String(32), nullable=False)
    confirmed = db.Column(db.Boolean, default=False) # Подтвержден ли аккаунт
    confirmed_at = db.Column(db.DateTime, nullable=True) # Время подтверждения
    failed_login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True) # Релизовать как активного пользователя в данный момент на сайте 
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        """Хеширование пароля с солью."""
        salt = secrets.token_hex(16)  # Генерация случайной соли (16 байт = 32 символа)
        self.salt = salt  # Сохраняем соль в базе данных
        self.password_hash = generate_password_hash(password + salt)  # Хешируем пароль с солью

    def check_password(self, password):
        """Проверка пароля с учетом соли."""
        return check_password_hash(self.password_hash, password + self.salt)
    
    def generate_confirmation_token(self, expires_sec=3600):
        """Создает токен для подтверждения учетной записи."""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})
        
    @staticmethod
    def verify_confirmation_token(token):
        """Проверяет токен подтверждения."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return data.get('confirm')

    def confirm(self):
        """Подтверждает аккаунт пользователя."""
        self.confirmed = True
        self.confirmed_at = datetime.utcnow()

    def __repr__(self):
        return f'<User {self.username}>'

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)  # Уникальный идентификатор
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # ID пользователя
    action = db.Column(db.String(255), nullable=False)  # Описание действия
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Время действия
    details = db.Column(db.Text, nullable=True)  # Дополнительные сведения

    def __repr__(self):
        return f"<Log {self.action} by User {self.user_id} at {self.timestamp}>"

    
