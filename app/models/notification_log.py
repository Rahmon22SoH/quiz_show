from datetime import datetime
from app.extensions import db

class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz_sessions.id'), nullable=True, index=True)
    message = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(32), nullable=False)  # 'success' или 'error'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    transport = db.Column(db.String(32), nullable=False, default='telegram')

    def __repr__(self):
        return f"<NotificationLog user_id={self.user_id} quiz_id={self.quiz_id} status={self.status} transport={self.transport}>" 