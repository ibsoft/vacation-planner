import os
import json
import logging
import logging.handlers
from flask import Flask, request, session
from config import Config, LOG_DIR
from app.extensions import db, migrate, login_manager, babel, csrf
from flask_session import Session


def _load_ldap_settings(app):
    try:
        from app.models.setting import LdapSetting
        config_map = {
            'LDAP_SERVER': 'ldap_server',
            'LDAP_BASE_DN': 'ldap_base_dn',
            'LDAP_BIND_DN': 'ldap_bind_dn',
            'LDAP_BIND_PASSWORD': 'ldap_bind_password',
            'LDAP_USER_FILTER': 'ldap_user_filter',
            'LDAP_USERNAME_ATTR': 'ldap_username_attr',
            'LDAP_EMAIL_ATTR': 'ldap_email_attr',
            'LDAP_DEPT_ATTR': 'ldap_dept_attr',
            'LDAP_MANAGER_ATTR': 'ldap_manager_attr',
            'LDAP_DISPLAY_NAME_ATTR': 'ldap_display_name_attr',
        }
        defaults = {
            'LDAP_USER_FILTER': '(&(objectClass=user)(objectCategory=person))',
            'LDAP_USERNAME_ATTR': 'sAMAccountName',
            'LDAP_EMAIL_ATTR': 'mail',
            'LDAP_DEPT_ATTR': 'department',
            'LDAP_MANAGER_ATTR': 'manager',
            'LDAP_DISPLAY_NAME_ATTR': 'displayName',
            'LDAP_SERVER': '',
            'LDAP_BASE_DN': '',
            'LDAP_BIND_DN': '',
            'LDAP_BIND_PASSWORD': '',
        }
        for config_key, default in defaults.items():
            db_val = LdapSetting.get(config_key)
            app.config[config_key] = db_val if db_val is not None else default
    except Exception:
        pass


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'flask_session')
    app.config['SESSION_PERMANENT'] = False
    Session(app)

    app.config['LDAP_SETTINGS'] = {}

    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance'), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    app.config['LOG_DIR'] = LOG_DIR

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            }
            if record.exc_info and record.exc_info[0]:
                log_entry['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_entry)

    json_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.jsonl'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    json_handler.setFormatter(JsonFormatter())
    json_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(json_handler)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        _load_ldap_settings(app)
        _load_email_settings(app)

    from datetime import datetime
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    def get_locale():
        if 'lang' in session:
            return session['lang']
        if request.args.get('lang'):
            session['lang'] = request.args.get('lang')
            return session['lang']
        try:
            from flask_login import current_user
            if current_user.is_authenticated and current_user.locale:
                return current_user.locale
        except Exception:
            pass
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'

    babel.init_app(app, locale_selector=get_locale)

    from app.routes import auth, admin, hr, manager, vacation, calendar_main, notifications
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(hr.bp)
    app.register_blueprint(manager.bp)
    app.register_blueprint(vacation.bp)
    app.register_blueprint(calendar_main.bp)
    app.register_blueprint(notifications.bp)

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models.department import Department
        from app.models.notification import Notification
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            recent_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
        else:
            unread_count = 0
            recent_notifications = []
        return {
            'current_user': current_user,
            'departments': Department.query.all() if current_user.is_authenticated else [],
            'enumerate': enumerate,
            'now': datetime.now,
            'unread_count': unread_count,
            'recent_notifications': recent_notifications,
        }

    @app.after_request
    def security_headers(response):
        csp = (
            "default-src 'self';"
            "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval';"
            "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.jsdelivr.net 'unsafe-inline';"
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.jsdelivr.net data:;"
            "img-src 'self' https://www.gravatar.com https://cdn.jsdelivr.net data: blob:;"
            "connect-src 'self';"
            "frame-ancestors 'none';"
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app


def _load_email_settings(app):
    try:
        from app.models.setting import EmailSetting
        keys = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM', 'SMTP_USE_TLS', 'SMTP_NO_AUTH', 'SMTP_TEXT_ONLY']
        defaults = {
            'SMTP_SERVER': '',
            'SMTP_PORT': '587',
            'SMTP_USER': '',
            'SMTP_PASSWORD': '',
            'SMTP_FROM': '',
            'SMTP_USE_TLS': '1',
            'SMTP_NO_AUTH': '0',
            'SMTP_TEXT_ONLY': '0',
        }
        for key in keys:
            db_val = EmailSetting.get(key)
            app.config[key] = db_val if db_val is not None else defaults.get(key, '')
    except Exception:
        pass
