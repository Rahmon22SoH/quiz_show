from datetime import datetime
import secrets
from app.extensions import db
from app.models.base import BaseModel

class QuizSession(BaseModel):
    """Сессия квиза (цикл)."""
    __tablename__ = 'quiz_sessions'
    
    # Добавляем индекс для оптимизации поиска по статусу
    __table_args__ = (
        db.Index('idx_quiz_status', 'status'),
        db.Index('idx_quiz_start_time', 'start_time'),
    )

    seed = db.Column(db.String(32), default=lambda: secrets.token_hex(16), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    total_amount = db.Column(db.Integer, default=0)  # Общая сумма ставок
    status = db.Column(db.String(20), default='pending')  # pending, active, finished
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    entry_fee = db.Column(db.Integer, default=100)  # Фиксированная сумма для входа в квиз
    
    # Логирование завершения квиза
    finished_by_admin = db.Column(db.Boolean, default=False)  # Досрочное завершение
    finished_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Кто завершил
    finished_without_participants = db.Column(db.Boolean, default=False)  # Завершен без участников

    # Отношения
    participants = db.relationship('QuizParticipant', backref='quiz', lazy='dynamic')
    winner = db.relationship('User', foreign_keys=[winner_id])

    # Добавляем новое поле
    single_participant = db.Column(db.Boolean, default=False)  # Флаг для квизов с одним участником

    def __repr__(self):
        return f'<QuizSession {self.id} ({self.status})>'
    
    def get_participants(self):
        """Возвращает список участников квиза."""
        from app.models.quiz_participant import QuizParticipant
        return QuizParticipant.query.filter_by(quiz_id=self.id).all()
    
    def start(self):
        """Переводит квиз из ожидания (pending) в активный (active)."""
        self.status = 'active'
        self.start_time = datetime.utcnow()
        return self.save()

    def is_expired(self):
        """Проверяет, истекло ли время квиза."""
        return datetime.utcnow() > self.end_time if self.end_time else False

    def finish(self, finished_by_admin=False, admin_id=None):
        """Завершает квиз и выбирает победителя."""
        from app.models import User
        from app.models.quiz_winners import QuizWinners
        
        try:
            self.status = 'finished'
            self.finished_by_admin = finished_by_admin
            if admin_id:
                self.finished_by = admin_id

            # Выбираем победителя
            participants = self.get_participants()
            if participants:
                winner = secrets.choice(participants)
                self.winner_id = winner.user_id
                
                # Начисляем выигрыш
                winner_user = User.query.get(winner.user_id)
                if winner_user:
                    winner_user.balance += self.total_amount
                    
                    # Создаем запись в истории победителей
                    winner_record = QuizWinners(
                        quiz_id=self.id,
                        user_id=winner.user_id,
                        prize_amount=self.total_amount
                    )
                    if not winner_record.save():
                        raise Exception("Failed to save winner record")
                    
            if not self.save():
                raise Exception("Failed to save quiz session")
                
            print(f"Quiz {self.id} finished successfully. Winner ID: {self.winner_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error finishing quiz {self.id}: {e}")
            raise 