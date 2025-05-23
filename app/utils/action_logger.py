from app.extensions import db
from app.models import Log
import logging

logger = logging.getLogger(__name__)

def log_action(action, details=None, user_id=None):
    """Логирование действий пользователей."""
    try:
        log = Log(
            user_id=user_id,
            action=action,
            details=details
        )
        if not log.save():
            logger.error(f"Failed to save log entry: {action}")
    except Exception as e:
        logger.error(f"Error logging action: {str(e)}")
        # Не позволяем ошибке логирования прервать основной процесс
        pass 