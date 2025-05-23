from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime

class Log(BaseModel):
    """Модель для логирования действий пользователей и системных событий"""
    __tablename__ = 'logs'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True)
    
    # Дополнительные поля для системных логов
    level = db.Column(db.String(20), nullable=True)  # INFO, WARNING, ERROR, CRITICAL, DEBUG
    message = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(100), nullable=True)
    function = db.Column(db.String(100), nullable=True)
    line = db.Column(db.Integer, nullable=True)
    
    # Отношения
    user = db.relationship('User', backref=db.backref('logs', lazy='dynamic'))
    
    def __repr__(self):
        if self.action:
            return f"<Log {self.action} by User {self.user_id} at {self.timestamp}>"
        else:
            return f"<Log {self.level}: {self.message} at {self.timestamp}>" 