from flask_login import current_user
from functools import wraps
from flask import abort, flash
from flask_babel import gettext as _


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def hr_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_hr or current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def manager_or_hr_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.is_hr or current_user.is_admin:
            return f(*args, **kwargs)
        from app.models import User
        has_subordinates = User.query.filter_by(manager_id=current_user.id).first() is not None
        if not has_subordinates:
            flash(_('You have no subordinates to manage.'), 'warning')
            return f(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function


def log_audit(action, details=None):
    from app.extensions import db
    from app.models.audit import AuditLog
    from flask import request
    log = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        username=current_user.username if current_user.is_authenticated else None,
        action=action,
        details=details,
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
