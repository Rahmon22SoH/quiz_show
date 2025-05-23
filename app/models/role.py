from app.extensions import db
from app.models.base import BaseModel

class Role(BaseModel):
    """Модель роли пользователя"""
    __tablename__ = 'roles'
    
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>' 