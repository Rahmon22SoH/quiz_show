from flask import render_template, redirect, url_for, flash
from flask_login import current_user, logout_user
from app.main import main
from app.utils.error_handlers import handle_error
from app.celery.tasks import test_task
#from app.utils.logger import log_info, log_warning
from app.auth.session import check_session_valid, clear_session
import time


@main.route('/')
@main.route('/index')
def index():
    """Главная страница"""
    try:
        # Упрощенный рендеринг главной страницы без данных о квизах
        return render_template('index.html')
    except Exception as e:
        return handle_error(e)

#@main.route('/test-celery')
#def test_celery():
#    """Тестовый маршрут для проверки работы Celery."""
#    task = test_task.delay()
#    return f"Task started with id {task.id}. Check console for results."

@main.before_request
def check_user_session():
    """Проверка сессии пользователя перед каждым запросом с логированием времени выполнения."""
    start_time = time.time()
    if current_user.is_authenticated:
        # Проверка валидности сессии
        if not check_session_valid():
            #log_info(f"Invalid session for user {current_user.username}")
            clear_session()
            logout_user()
            flash('Сессия истекла. Пожалуйста, войдите снова.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Проверка блокировки пользователя
        if not current_user.is_active:
            #log_warning(f"Blocked user {current_user.username} tried to access the site")
            logout_user()
            clear_session()
            flash('Ваш аккаунт заблокирован администрацией. Доступ запрещен.', 'danger')
            return redirect(url_for('auth.login'))
    duration = (time.time() - start_time) * 1000
    if duration > 100:
        print(f"[check_user_session] slow: {duration:.2f} ms")