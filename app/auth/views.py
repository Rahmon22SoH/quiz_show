# app/auth/views.py

from flask import render_template, flash, redirect, url_for, request,jsonify, session
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from app.auth import auth
from app.utils.logger import log_error
from app.models import User
from app.extensions import db
from app.auth.session import init_session, clear_session, check_session_valid
from app.utils.error_handlers import handle_error
from urllib.parse import urlparse  # Исправлено с url_parse на urlparse
from ..extensions import csrf # <--- Импортируем из extensions --- НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ без защиты УБРАТЬ ДЛЯ ТЕСТОВ 
from app.utils.logger import log_event, make_details

@auth.route('/login')
def login():
    """Страница входа через Telegram."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('auth/telegram_login.html')

@auth.route('/logout')
def logout():
    """Выход из системы."""
    if current_user.is_authenticated:
        log_event(
            action="logout",
            user_id=current_user.id,
            details=f"Logout user: {current_user.username}, IP: {request.remote_addr}",
            level="INFO",
            message="Пользователь вышел из системы",
            module=__name__,
            function="logout"
        )
        clear_session()
        logout_user()
    return redirect(url_for('main.index'))

@auth.route('/telegram-callback', methods=['GET', 'POST'])
def telegram_callback():
    try:
        print("Telegram callback received")
        if request.method == 'POST':
            auth_data = request.get_json()
            print("POST data received:", auth_data)
        else:
            # Для GET запроса от Telegram виджета
            auth_data = request.args.to_dict()
            print("GET data received:", auth_data)
            
            # Преобразуем данные в нужный формат
            telegram_data = {
                'telegram_id': auth_data.get('id'),  # Для GET запроса используем 'id'
                'first_name': auth_data.get('first_name'),
                'last_name': auth_data.get('last_name'),
                'username': auth_data.get('username'),
                'photo_url': auth_data.get('photo_url'),
                'auth_date': auth_data.get('auth_date'),
                'hash': auth_data.get('hash'),
                'phone': auth_data.get('phone')  # Добавляем phone, если есть
            }

            # Извлечение ссылки на профиль Telegram
            telegram_link = f'https://t.me/{telegram_data["username"]}' if telegram_data.get('username') else None

            # Создаем/получаем пользователя
            user = User.get_or_create_from_telegram(telegram_data, telegram_link)
            if not user:
                raise ValueError("Failed to create/get user")

            # Выполняем вход
            login_user(user, remember=True)
            
            # Инициализируем сессию
            init_session(user)
            
            # Логируем успешный вход
            log_event(
                action="login_success",
                user_id=user.id,
                details=make_details(user_id=user.id, username=user.username, ip=request.remote_addr),
                level="INFO",
                message="Пользователь успешно вошёл через Telegram",
                module=__name__,
                function="telegram_callback"
            )
            
            # Для GET запроса делаем прямой редирект
            redirect_url = user.get_redirect_url()
            return redirect(redirect_url)

        # Обработка POST запроса остается прежней
        if not auth_data:
            raise ValueError("No authentication data received")

        telegram_data = {
            'telegram_id': auth_data.get('telegram_id') or auth_data.get('id'),
            'first_name': auth_data.get('first_name'),
            'last_name': auth_data.get('last_name'),
            'username': auth_data.get('username'),
            'photo_url': auth_data.get('photo_url'),
            'auth_date': auth_data.get('auth_date'),
            'phone': auth_data.get('phone')  # Добавляем phone, если есть
        }

        # Извлечение ссылки на профиль Telegram
        telegram_link = f'https://t.me/{telegram_data["username"]}' if telegram_data.get('username') else None

        user = User.get_or_create_from_telegram(telegram_data, telegram_link)
        if not user:
            raise ValueError("Failed to create/get user")

        login_user(user, remember=True)
        init_session(user)
        log_event(
            action="login_success",
            user_id=user.id,
            details=make_details(user_id=user.id, username=user.username, ip=request.remote_addr),
            level="INFO",
            message="Пользователь успешно вошёл через Telegram",
            module=__name__,
            function="telegram_callback"
        )
        
        redirect_url = user.get_redirect_url()
        print(f"Redirect URL for user {user.username}: {redirect_url}")

        return jsonify({
            'success': True,
            'redirect': redirect_url,
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin,
                'role': user.role.name if user.role else 'user'
            }
        })

    except Exception as e:
        print(f"Error in telegram_callback: {str(e)}")
        log_event(
            action="login_failed",
            user_id=None,
            details=f"Ошибка аутентификации через Telegram: {str(e)}, IP: {request.remote_addr}",
            level="WARNING",
            message="Ошибка входа через Telegram",
            module=__name__,
            function="telegram_callback"
        )
        return jsonify({'error': str(e)}), 500

@auth.route('/check-auth')
def check_auth():
    """Проверка статуса авторизации пользователя."""
    try:
        if current_user.is_authenticated and check_session_valid():
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'role': current_user.role.name if current_user.role else 'user',
                    'is_admin': current_user.is_admin,
                    'photo_url': current_user.telegram_photo_url
                }
            })
        return jsonify({'authenticated': False})
    except Exception as e:
        print(f"Error in check_auth: {str(e)}")
        clear_session()
        return jsonify({'authenticated': False, 'error': str(e)}), 500

# Функция для проверки данных от Telegram
def validate_telegram_data(telegram_data):
    """
    Проверяет данные, полученные от Telegram Login Widget.
    
    Args:
        telegram_data (dict): Данные от Telegram Login Widget
        
    Returns:
        bool: True если данные валидны, False в противном случае
    """
    try:
        # Проверяем наличие обязательных полей
        required_fields = ['id', 'first_name', 'auth_date']
        for field in required_fields:
            if field not in telegram_data:
                log_error(f"Missing required field in Telegram data: {field}")
                return False
        
        # Проверяем, что auth_date не слишком старый (не более 1 дня)
        auth_date = int(telegram_data['auth_date'])
        current_time = int(datetime.now().timestamp())
        if current_time - auth_date > 86400:  # 86400 секунд = 1 день
            log_error(f"Telegram auth_date too old: {auth_date}, current: {current_time}")
            return False
        
        # Здесь можно добавить проверку подписи данных, если это необходимо
        # ...
        
        # Преобразуем id в telegram_id для совместимости с моделью
        telegram_data['telegram_id'] = telegram_data.pop('id')
        
        return True
    except Exception as e:
        log_error(f"Error validating Telegram data: {str(e)}")
        return False

@auth.route('/telegram-login')
def telegram_login():
    """Обработка входа через Telegram."""
    try:
        # Получаем данные от Telegram
        telegram_data = request.args.to_dict()
        
        # Проверяем данные
        if not validate_telegram_data(telegram_data):
            flash('Ошибка аутентификации через Telegram. Пожалуйста, попробуйте снова.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Получаем или создаем пользователя
        user = User.get_or_create_from_telegram(telegram_data)
        
        # Входим пользователя
        login_user(user, remember=True)
        
        # Создаем сессию
        init_session(user.id)  # Используем init_session 
        
        # Логируем вход
        log_event(
            action="login_success",
            user_id=user.id,
            details=make_details(user_id=user.id, username=user.username, ip=request.remote_addr),
            level="INFO",
            message="Пользователь успешно вошёл через Telegram",
            module=__name__,
            function="telegram_login"
        )
        
        # Перенаправляем на нужную страницу
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = user.get_redirect_url()
        
        return redirect(next_page)
    except Exception as e:
        log_event(
            action="login_failed",
            user_id=None,
            details=f"Ошибка аутентификации через Telegram: {str(e)}, IP: {request.remote_addr}",
            level="WARNING",
            message="Ошибка входа через Telegram",
            module=__name__,
            function="telegram_login"
        )
        flash('Произошла ошибка при входе через Telegram. Пожалуйста, попробуйте снова.', 'danger')
        return redirect(url_for('auth.login'))

# --- Маршрут ТОЛЬКО для тестов Locust --- НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ без защиты! УБРАТЬ ДЛЯ ТЕСТОВ
@auth.route('/_locust_login_', methods=['POST'])
@csrf.exempt # <--- Отключаем CSRF-защиту для этого маршрута
def locust_login():
    from flask import current_app # Импортируем здесь
    current_app.logger.info(f"_locust_login_ received request. Headers: {request.headers}") # Логируем заголовки
    current_app.logger.info(f"_locust_login_ request.is_json: {request.is_json}") # Проверяем is_json
    # Опционально: Добавить проверку, что приложение в режиме отладки/тестирования
    # if not current_app.config.get('DEBUG') and not current_app.config.get('TESTING'):
    if not request.is_json:
        current_app.logger.error("_locust_login_ failed: request.is_json is False") # Логируем ошибку
        return jsonify({'error': 'Request must be JSON'}), 400

    # Добавим лог перед get_json
    current_app.logger.info("_locust_login_ trying to get JSON data...")
    try:
        data = request.get_json()
        current_app.logger.info(f"_locust_login_ received data: {data}")
    except Exception as e:
        current_app.logger.error(f"_locust_login_ failed: Error getting JSON data: {e}")
        return jsonify({'error': 'Failed to parse JSON'}), 400

    username = data.get('username')
    current_app.logger.info(f"_locust_login_ extracted username: {username}")

    if not username:
        current_app.logger.error("_locust_login_ failed: Missing username in JSON") # Логируем ошибку
        return jsonify({'error': 'Missing username'}), 400

    user = User.query.filter_by(username=username).first()

    if user:
        current_app.logger.info(f"User {username} found. Role ID: {user.role_id}") # Log role_id
        login_user(user)
        current_app.logger.info(f"User {username} logged in via login_user. Current user: {current_user.username}")
        current_app.logger.info(f"Attempting init_session for user {user.username}")
        init_session(user) # <-- Calls the function
        current_app.logger.info(f"init_session completed for user {user.username}")
        log_event(
            action="login_success",
            user_id=user.id,
            details=f"Login for testing: {user.username}",
            level="INFO",
            message="Пользователь успешно вошёл для тестирования",
            module=__name__,
            function="locust_login"
        )
        current_app.logger.info(f"Session after login: {dict(session)}") # <--- Добавляем лог сессии
        return jsonify({'status': 'ok', 'message': f'User {username} logged in for testing.'}), 200
    else:
        log_event(
            action="login_failed",
            user_id=None,
            details=f"Locust Login Attempt Failed: User '{username}' not found.",
            level="WARNING",
            message="Попытка входа для тестирования не удалась",
            module=__name__,
            function="locust_login"
        )
        return jsonify({'error': f'User {username} not found'}), 404
# ---
