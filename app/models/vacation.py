from app.extensions import db


class VacationCause(db.Model):
    __tablename__ = 'vacation_causes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    name_el = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<VacationCause {self.name}>'


class VacationRequest(db.Model):
    __tablename__ = 'vacation_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_count = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    request_type = db.Column(db.String(20), default='user')
    cause_id = db.Column(db.Integer, db.ForeignKey('vacation_causes.id'), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    change_requested_start = db.Column(db.Date, nullable=True)
    change_requested_end = db.Column(db.Date, nullable=True)
    change_reason = db.Column(db.Text, nullable=True)
    change_status = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    user = db.relationship('User', foreign_keys=[user_id], backref='vacation_requests', lazy=True)
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_requests', lazy=True)
    cause = db.relationship('VacationCause', backref='vacation_requests', lazy=True)

    def __repr__(self):
        return f'<VacationRequest {self.user_id} {self.start_date}-{self.end_date}>'


class VacationAssignment(db.Model):
    __tablename__ = 'vacation_assignments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    cause_id = db.Column(db.Integer, db.ForeignKey('vacation_causes.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', foreign_keys=[user_id], backref='assigned_days', lazy=True)
    cause = db.relationship('VacationCause', backref='assignments', lazy=True)
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='assigned_by', lazy=True)

    def __repr__(self):
        return f'<VacationAssignment {self.user_id} {self.date}>'
