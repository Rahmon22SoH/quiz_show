from flask import session
from datetime import datetime
from functools import wraps
from flask_login import current_user
from app.utils.logger import log_error
import time

def init_session(user):
    """Инициализация сессии при входе пользователя."""
    session.permanent = True
    session['user_id'] = user.id
    session['login_time'] = datetime.utcnow().timestamp()
    session['_fresh'] = True
    session['role'] = user.role.name if user.role else 'user'
    session['is_authenticated'] = True  # Добавляем явный флаг аутентификации

def clear_session():
    """Очистка сессии при выходе пользователя."""
    session.clear()

def check_session_valid():
    """Проверяет валидность текущей сессии и минимизирует обращения к БД и обновления сессии. Подробное логирование."""
    start_time = time.time()
    try:
        t0 = time.time()
        if not current_user.is_authenticated:
            print(f"[check_session_valid] not authenticated: {(time.time()-t0)*1000:.2f} ms")
            return False
        t1 = time.time()
        session_modified = False
        # Проверяем user_id
        if session.get('user_id') != current_user.id:
            session['user_id'] = current_user.id
            session_modified = True
        t2 = time.time()
        # Проверяем is_authenticated
        if not session.get('is_authenticated', False):
            session['is_authenticated'] = True
            session_modified = True
        t3 = time.time()
        # Проверяем login_time
        if not session.get('login_time'):
            session['login_time'] = datetime.utcnow().timestamp()
            session_modified = True
        t4 = time.time()
        # Проверяем роль (используем кэш из сессии, если есть)
        current_role = getattr(getattr(current_user, 'role', None), 'name', 'user')
        if session.get('role') != current_role:
            session['role'] = current_role
            session_modified = True
        t5 = time.time()
        if session_modified:  # <-- Раскомментируем
            session.modified = True # <-- Раскомментируем
        t6 = time.time()
        print(f"[check_session_valid] times: auth={((t1-t0)*1000):.2f}ms, user_id={((t2-t1)*1000):.2f}ms, is_auth={((t3-t2)*1000):.2f}ms, login_time={((t4-t3)*1000):.2f}ms, role={((t5-t4)*1000):.2f}ms, session_mod={((t6-t5)*1000):.2f}ms, total={(time.time()-start_time)*1000:.2f}ms")
        return True
    except Exception as e:
        log_error(f"Session validation error: {str(e)}")
        return False

def session_required(f):
    """Декоратор для проверки сессии."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Просто проверяем и обновляем сессию без перенаправления
        check_session_valid()
        return f(*args, **kwargs)
    return decorated_function 