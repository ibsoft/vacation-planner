from flask_wtf import FlaskForm
from wtforms import RadioField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext as _l


class ApprovalForm(FlaskForm):
    action = RadioField(_l('Action'), choices=[
        ('approved', _l('Approve')),
        ('rejected', _l('Reject'))
    ], validators=[DataRequired()])
    comment = TextAreaField(_l('Comment'))
    submit = SubmitField(_l('Submit'))
