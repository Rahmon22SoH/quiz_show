import hashlib
import hmac
import time
from flask import current_app
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

def verify_telegram_data(auth_data):
    """
    Проверяет подпись данных от Telegram Login Widget.
    
    Args:
        auth_data (dict): Данные, полученные от Telegram Login Widget
        
    Returns:
        bool: True если данные валидны, False в противном случае
    """
    try:
        if not auth_data or 'hash' not in auth_data:
            current_app.logger.warning("No hash in Telegram auth data")
            return False
            
        # Проверяем актуальность auth_date
        auth_date = datetime.fromtimestamp(int(auth_data.get('auth_date', 0)))
        if datetime.now() - auth_date > timedelta(days=1):  # Данные устарели
            current_app.logger.warning("Telegram auth data expired")
            return False
        
        # Формируем строку для проверки подписи
        check_hash = auth_data.pop('hash')
        data_check_arr = []
        
        for key, value in sorted(auth_data.items()):
            if value is not None:
                data_check_arr.append(f"{key}={value}")
        
        data_check_string = "\n".join(data_check_arr)
        
        # Создаем секретный ключ
        secret_key = hashlib.sha256(
            current_app.config['TELEGRAM_BOT_TOKEN'].encode()
        ).digest()
        
        # Вычисляем хеш
        hmac_obj = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        )
        
        # Возвращаем hash обратно в словарь
        auth_data['hash'] = check_hash
        
        # Сравниваем хеши
        is_valid = hmac_obj.hexdigest() == check_hash
        if not is_valid:
            current_app.logger.warning("Invalid Telegram data hash")
            
        return is_valid
        
    except Exception as e:
        current_app.logger.error(f"Error verifying Telegram data: {str(e)}")
        return False

def format_telegram_data(auth_data):
    """
    Форматирует данные от Telegram для создания/обновления пользователя.
    
    Args:
        auth_data (dict): Данные от Telegram Login Widget
        
    Returns:
        dict: Отформатированные данные пользователя
    """
    return {
        'telegram_id': str(auth_data.get('id')),
        'first_name': auth_data.get('first_name', ''),
        'last_name': auth_data.get('last_name', ''),
        'username': auth_data.get('username', ''),
        'photo_url': auth_data.get('photo_url', ''),
        'auth_date': datetime.fromtimestamp(int(auth_data.get('auth_date', 0)))
    }

def get_telegram_user_data(data: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Извлекает и проверяет данные пользователя из Telegram.
    
    Args:
        data: Словарь с данными от Telegram
        
    Returns:
        Optional[Dict[str, str]]: Словарь с данными пользователя или None если данные невалидны
    """
    if not verify_telegram_data(data):
        return None
    
    return {
        'telegram_id': data.get('id'),
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'username': data.get('username', ''),
        'photo_url': data.get('photo_url', ''),
        'auth_date': data.get('auth_date')
    }
