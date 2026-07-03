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
