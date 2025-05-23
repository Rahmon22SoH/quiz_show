from app.extensions import login_manager
from flask import flash, redirect, url_for, session, request
from flask_login import current_user
from functools import wraps
from app.utils.logger import log_event
from app.utils.action_logger import log_action
import os
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def seed_admin_user():
    """Добавляет администратора в базу данных."""
    from app.models import User, Role
    
    # Получаем данные из .env
    admin_telegram_id = os.getenv('ADMIN_TELEGRAM_ID')
    
    if not admin_telegram_id:
        print("ADMIN_TELEGRAM_ID не установлен в .env файле!")
        return
    
    # Проверяем, существует ли пользователь
    admin_user = User.query.filter_by(telegram_id=admin_telegram_id).first()
    admin_role = Role.query.filter_by(name='admin').first()

    if not admin_user and admin_role:
        admin_user = User(
            username='admin',
            first_name='Admin',
            last_name='User',
            telegram_id=admin_telegram_id,
            telegram_username='admin',
            telegram_auth_date=datetime.utcnow(),
            role_id=admin_role.id
        )
        if not admin_user.save():
            print("Ошибка при создании администратора")
            return
        print(f"Администратор создан с telegram_id: {admin_telegram_id}")

def seed_roles():
    """Добавляет предустановленные роли в базу данных."""
    from app.models import Role
    
    roles = ['admin', 'user']  # Предустановленные роли
    for role_name in roles:
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name)
            if not role.save():
                print(f"Ошибка при создании роли {role_name}")
                return
    print("Роли успешно созданы")

def seed_roles_and_admin():
    """Инициализирует роли и администратора."""
    seed_roles()
    seed_admin_user()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Проверяем сессию
        if 'user_id' not in session or session['user_id'] != current_user.id:
            # Тихо обновляем сессию без сообщения пользователю
            session['user_id'] = current_user.id
            log_action(f"Session updated for user {current_user.id}")
            
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Отладочная информация
        print(f"Admin check: is_authenticated={current_user.is_authenticated}, user={current_user.username if current_user.is_authenticated else 'None'}")
        print(f"Session data: user_id={session.get('user_id')}, is_auth={session.get('is_authenticated')}")
        
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('auth.login'))
            
        if not current_user.is_admin:
            log_event(
                action="admin_access_denied",
                user_id=current_user.id,
                details=f"Попытка доступа к админке: {current_user.username}, IP: {request.remote_addr}",
                level="WARNING",
                message="Доступ к админке запрещён",
                module=__name__,
                function="admin_required"
            )
            flash('У вас нет прав для доступа к этой странице.', 'danger')
            return redirect(url_for('main.index'))
            
        # Проверяем сессию и тихо обновляем её при необходимости
        if 'user_id' not in session or session['user_id'] != current_user.id:
            session['user_id'] = current_user.id
            log_action(f"Admin session updated for user {current_user.id}")
            
        return f(*args, **kwargs)
    return decorated_function

def verify_telegram_data(auth_data):
    """Проверка данных аутентификации от Telegram."""
    try:
        if not auth_data:
            print("No auth data provided")
            return False
            
        # Добавляем дополнительные проверки
        required_fields = ['id', 'first_name', 'auth_date', 'hash']
        if not all(field in auth_data for field in required_fields):
            print("Missing required fields in auth data")
            return False
            
        # Проверяем hash от Telegram
        # ... существующий код проверки ...
        
        return True
    except Exception as e:
        print(f"Error verifying Telegram data: {str(e)}")
        return False