from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notification import Notification

bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notification = db.session.get(Notification, notif_id)
    if notification and notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    return jsonify({'ok': True})


@bp.route('/recent', methods=['GET'])
@login_required
def recent_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    return jsonify({
        'notifications': [
            {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'link': notif.link,
                'type': notif.type,
                'created_at': notif.created_at.strftime('%d/%m/%Y %H:%M') if notif.created_at else ''
            }
            for notif in notifications
        ]
    })


@bp.route('/clear', methods=['POST'])
@login_required
def clear_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({'ok': True})
