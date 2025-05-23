from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel

class QuizParticipant(BaseModel):
    """Участник квиза."""
    __tablename__ = 'quiz_participants'
    
    # Добавляем составной индекс для оптимизации поиска участия
    __table_args__ = (
        db.Index('idx_quiz_participant', 'quiz_id', 'user_id'),
        db.Index('idx_participant_user', 'user_id'),
    )

    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Сумма участия
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Отношения
    user = db.relationship('User', backref=db.backref('quiz_participations', lazy='dynamic'))

    def __repr__(self):
        return f'<QuizParticipant {self.user_id} in Quiz {self.quiz_id}>' 