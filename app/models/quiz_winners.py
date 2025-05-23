from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel

class QuizWinners(BaseModel):
    """История победителей квизов."""
    __tablename__ = 'quiz_winners'

    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prize_amount = db.Column(db.Integer, nullable=False)  # Сумма выигрыша
    platform_fee = db.Column(db.Integer, default=0)  # Комиссия платформы
    won_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_refund = db.Column(db.Boolean, default=False)  # Флаг возврата ставки (для одиночных участников)

    # Отношения
    quiz = db.relationship('QuizSession', backref=db.backref('winners', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('winnings', lazy='dynamic'))

    def __repr__(self):
        return f'<QuizWinner quiz_id={self.quiz_id} user_id={self.user_id} amount={self.prize_amount}>' 