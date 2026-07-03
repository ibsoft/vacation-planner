from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional
from flask_babel import lazy_gettext as _l


class VacationRequestForm(FlaskForm):
    start_date = DateField(_l('Start Date'), validators=[DataRequired()])
    end_date = DateField(_l('End Date'), validators=[DataRequired()])
    cause_id = SelectField(_l('Vacation Cause'), coerce=int, validators=[DataRequired()])
    custom_reason = TextAreaField(_l('Custom Reason'), validators=[Optional()])
    submit = SubmitField(_l('Submit Request'))


class ChangeRequestForm(FlaskForm):
    start_date = DateField(_l('New Start Date'), validators=[DataRequired()])
    end_date = DateField(_l('New End Date'), validators=[DataRequired()])
    change_reason = TextAreaField(_l('Reason for Change'), validators=[DataRequired()])
    submit = SubmitField(_l('Submit Change Request'))


class VacationEditForm(FlaskForm):
    start_date = DateField(_l('Start Date'), validators=[DataRequired()])
    end_date = DateField(_l('End Date'), validators=[DataRequired()])
    submit = SubmitField(_l('Save Changes'))
