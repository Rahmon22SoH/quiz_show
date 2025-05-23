from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel

class PlatformStats(BaseModel):
    """Статистика платформы."""
    __tablename__ = 'platform_stats'
    
    # Финансовые показатели
    total_revenue = db.Column(db.Integer, default=0)  # Общая прибыль платформы
    revenue_current_month = db.Column(db.Integer, default=0)  # Прибыль за текущий месяц
    revenue_previous_month = db.Column(db.Integer, default=0)  # Прибыль за предыдущий месяц
    
    # Метрики активности
    active_users_count = db.Column(db.Integer, default=0)  # Активные пользователи (участвовали в квизах)
    conversion_rate = db.Column(db.Float, default=0)  # Процент пользователей, участвующих в квизах
    
    # Служебная информация
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)  # Время последнего обновления
    
    def __repr__(self):
        return f'<PlatformStats revenue={self.total_revenue}>'
    
    def update_monthly_stats(self):
        """Обновляет месячную статистику."""
        from app.models import QuizWinners
        from sqlalchemy import func
        import calendar
        from datetime import datetime, timedelta
        
        # Получаем текущую дату
        now = datetime.utcnow()
        
        # Начало текущего месяца
        current_month_start = datetime(now.year, now.month, 1)
        
        # Начало предыдущего месяца
        if now.month == 1:
            prev_month_start = datetime(now.year - 1, 12, 1)
        else:
            prev_month_start = datetime(now.year, now.month - 1, 1)
        
        # Конец предыдущего месяца
        prev_month_end = current_month_start - timedelta(seconds=1)
        
        # Получаем сумму комиссий за текущий месяц
        current_month_revenue = db.session.query(
            func.sum(QuizWinners.platform_fee)
        ).filter(
            QuizWinners.won_at >= current_month_start
        ).scalar() or 0
        
        # Получаем сумму комиссий за предыдущий месяц
        previous_month_revenue = db.session.query(
            func.sum(QuizWinners.platform_fee)
        ).filter(
            QuizWinners.won_at >= prev_month_start,
            QuizWinners.won_at <= prev_month_end
        ).scalar() or 0
        
        # Обновляем статистику
        self.revenue_current_month = current_month_revenue
        self.revenue_previous_month = previous_month_revenue
        self.last_updated = now
        
        return self.save() 