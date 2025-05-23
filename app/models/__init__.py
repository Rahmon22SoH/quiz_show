# Импортируем все модели для доступа через app.models
from app.models.base import BaseModel
from app.models.user import User
from app.models.role import Role
from app.models.log import Log
from app.models.quiz_session import QuizSession
from app.models.quiz_participant import QuizParticipant
from app.models.quiz_winners import QuizWinners
from app.models.platform_stats import PlatformStats
from .notification_log import NotificationLog


# Экспортируем все модели
__all__ = [
    'BaseModel',
    'User', 
    'Role', 
    'Log',
    'QuizSession',
    'QuizParticipant',
    'QuizWinners',
    'PlatformStats',
] 