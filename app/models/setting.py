from app.extensions import db


class LdapSetting(db.Model):
    __tablename__ = 'ldap_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    @classmethod
    def get(cls, key, default=None):
        obj = cls.query.filter_by(key=key).first()
        return obj.value if obj else default

    @classmethod
    def set(cls, key, value):
        obj = cls.query.filter_by(key=key).first()
        if obj:
            obj.value = value
        else:
            obj = cls(key=key, value=value)
            db.session.add(obj)


class EmailSetting(db.Model):
    __tablename__ = 'email_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    @classmethod
    def get(cls, key, default=None):
        obj = cls.query.filter_by(key=key).first()
        return obj.value if obj else default

    @classmethod
    def set(cls, key, value):
        obj = cls.query.filter_by(key=key).first()
        if obj:
            obj.value = value
        else:
            obj = cls(key=key, value=value)
            db.session.add(obj)
