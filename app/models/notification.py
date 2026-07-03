from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    type = db.Column(db.String(20), default='info')
    link = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', order_by='Notification.created_at.desc()'))
