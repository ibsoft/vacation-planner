import os

basedir = os.path.abspath(os.path.dirname(__file__))
LOG_DIR = os.path.join(basedir, 'logs')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(64).hex())
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'vacations.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'Europe/Athens'
    LANGUAGES = {'en': 'English', 'el': 'Ελληνικά'}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FORCE_HTTPS', '0') == '1'
    WTF_CSRF_TIME_LIMIT = 3600

    LDAP_SERVER = os.environ.get('LDAP_SERVER', 'ldap://localhost:389')
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=example,dc=com')
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN', 'cn=admin,dc=example,dc=com')
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')
    LDAP_USER_FILTER = os.environ.get('LDAP_USER_FILTER', '(objectClass=user)')
    LDAP_USERNAME_ATTR = os.environ.get('LDAP_USERNAME_ATTR', 'sAMAccountName')
    LDAP_EMAIL_ATTR = os.environ.get('LDAP_EMAIL_ATTR', 'mail')
    LDAP_DEPT_ATTR = os.environ.get('LDAP_DEPT_ATTR', 'department')
    LDAP_MANAGER_ATTR = os.environ.get('LDAP_MANAGER_ATTR', 'manager')
    LDAP_DISPLAY_NAME_ATTR = os.environ.get('LDAP_DISPLAY_NAME_ATTR', 'displayName')
