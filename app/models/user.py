from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), nullable=True)
    display_name = db.Column(db.String(200), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_hr = db.Column(db.Boolean, default=False)
    is_top_management = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    locale = db.Column(db.String(5), default='en')
    email_locale = db.Column(db.String(5), nullable=True)

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    vacation_days_per_year = db.Column(db.Integer, default=20)

    ad_guid = db.Column(db.String(128), nullable=True, unique=True)
    ad_dn = db.Column(db.String(256), nullable=True)

    phone = db.Column(db.String(50), nullable=True)
    mobile = db.Column(db.String(50), nullable=True)
    internal_phone = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    department = db.relationship('Department', foreign_keys=[department_id], backref='members', lazy=True)
    manager = db.relationship('User', remote_side=[id], foreign_keys=[manager_id], backref='subordinates', lazy=True)

    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

    @property
    def is_manager(self):
        return User.query.filter_by(manager_id=self.id).first() is not None

    @property
    def remaining_days(self):
        from app.models.vacation import VacationRequest
        used = db.session.query(db.func.coalesce(db.func.sum(VacationRequest.days_count), 0))\
            .filter(VacationRequest.user_id == self.id,
                    VacationRequest.status.in_(['approved', 'hr_assigned']))\
            .scalar()
        return max(0, self.vacation_days_per_year - used)

    @property
    def gravatar_url(self):
        import hashlib
        email = (self.email or '').lower().strip()
        if not email:
            return 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&s=100'
        hash = hashlib.md5(email.encode()).hexdigest()
        return f'https://www.gravatar.com/avatar/{hash}?d=mp&s=100'

    def __repr__(self):
        return f'<User {self.username}>'
