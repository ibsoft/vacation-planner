from app.extensions import db


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    name_el = db.Column(db.String(100), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_department', lazy=True, post_update=True)

    def __repr__(self):
        return f'<Department {self.name}>'
