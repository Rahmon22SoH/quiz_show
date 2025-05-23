from datetime import datetime
from app.extensions import db

class BaseModel(db.Model):
    """Базовая модель с общими полями и методами"""
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        """Сохраняет запись в базу данных"""
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error saving {self.__class__.__name__}: {str(e)}")
            return False

    def delete(self):
        """Удаляет запись из базы данных"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting {self.__class__.__name__}: {str(e)}")
            return False 