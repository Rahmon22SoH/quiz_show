from app.extensions import db
from datetime import datetime
from decimal import Decimal

class DonationPayment(db.Model):
    __tablename__ = 'donation_payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(precision=12, scale=2), nullable=False)  # USD
    currency = db.Column(db.String(8), default='USD', nullable=False)
    status = db.Column(db.String(16), default='pending', nullable=False)  # pending, success, failed
    external_id = db.Column(db.String(64), nullable=True)  # ID платежа в DonationAlerts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('donation_payments', lazy='dynamic'))

    def __repr__(self):
        return f'<DonationPayment {self.id} {self.amount} {self.currency} {self.status}>' 