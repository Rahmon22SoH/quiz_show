from app.extensions import login_manager
from app.models import User, Role, db, Log
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, UserMixin
from flask import current_app, abort
from functools import wraps
from werkzeug.security import generate_password_hash
import os

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def seed_admin_user():
    """Добавляет суперпользователя (admin) в базу данных."""
    # Получаем данные из .env
    admin_email = current_app.config['ADMIN_EMAIL']
    admin_password = os.getenv('ADMIN_PASSWORD')  # Берем пароль из переменной окружения

    if admin_password:  # Проверяем, что пароль существует в .env
        password_hash = generate_password_hash(admin_password)  # Хешируем пароль
    else:
        raise ValueError("ADMIN_PASSWORD не установлен в переменных окружения!")

    # Проверяем, существует ли пользователь
    admin_user = User.query.filter_by(email=admin_email).first()
    admin_role = Role.query.filter_by(name='admin').first()

    if not admin_user and admin_role:
        admin_user = User(
            username='admin',
            email=admin_email,
            first_name='Admin',
            last_name='User',
            role_id=admin_role.id,
            confirmed=1
        )
        admin_user.set_password(admin_password)  # Устанавливаем пароль
        db.session.add(admin_user)
        db.session.commit()

def seed_roles():
        """Добавляет предустановленные роли в базу данных."""
        roles = ['admin', 'user']  # Предустановленные роли
        for role_name in roles:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name)
                db.session.add(role)
        db.session.commit()   

def seed_roles_and_admin():
    """Инициализирует роли и суперпользователя."""
    seed_roles()  # Добавляем роли
    seed_admin_user()  # Добавляем суперпользователя

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, авторизован ли пользователь и имеет ли он роль admin
        if not current_user.is_authenticated or not current_user.role or current_user.role.name != 'admin':
            flash('У вас нет разрешения на доступ к этой странице.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action, details=None, user_id=None):
    """Функция для записи логов пользователя."""
    if user_id is None:  # Если ID пользователя не передан
        if current_user.is_authenticated:
            user_id = current_user.id
        else:
            print("Error: current_user is not authenticated")  # Временный вывод
            raise ValueError("User ID is required for unauthenticated actions")

    try:
        log = Log(
            user_id=user_id,
            action=action,
            details=details
        )
        db.session.add(log)
        db.session.commit()
        print(f"Log added successfully: {log}")  # Успешный лог
    except Exception as e:
        db.session.rollback()  # Откатываем транзакцию
        print(f"Error while logging action: {e}")  # Вывод ошибки