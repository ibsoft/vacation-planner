from app.extensions import db


class GreekHoliday(db.Model):
    __tablename__ = 'greek_holidays'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    name_el = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<GreekHoliday {self.date} {self.name}>'
