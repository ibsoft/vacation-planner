from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SubmitField, DateField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_babel import lazy_gettext as _l


class SetVacationDaysForm(FlaskForm):
    vacation_days_per_year = IntegerField(_l('Vacation Days Per Year'),
                                          validators=[DataRequired(), NumberRange(min=0, max=365)])
    submit = SubmitField(_l('Update'))


class AssignVacationForm(FlaskForm):
    user_id = SelectField(_l('Employee'), coerce=int, validators=[DataRequired()])
    start_date = DateField(_l('Start Date'), validators=[DataRequired()])
    end_date = DateField(_l('End Date'), validators=[DataRequired()])
    cause_id = SelectField(_l('Cause'), coerce=int, validators=[DataRequired()])
    reason = TextAreaField(_l('Additional Notes'))
    submit = SubmitField(_l('Assign Vacation'))
