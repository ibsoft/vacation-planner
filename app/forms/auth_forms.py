from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, Email
from flask_babel import lazy_gettext as _l


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class ProfileForm(FlaskForm):
    display_name = StringField(_l('Display Name'), validators=[Optional()])
    email = StringField(_l('Email'), validators=[Optional(), Email()])
    phone = StringField(_l('Phone'), validators=[Optional()])
    mobile = StringField(_l('Mobile'), validators=[Optional()])
    internal_phone = StringField(_l('Internal Phone'), validators=[Optional()])
    locale = SelectField(_l('Language'), choices=[('en', 'English'), ('el', 'Ελληνικά')], default='en')
    avatar = FileField(_l('Avatar'), validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], _l('Images only!'))])
    submit = SubmitField(_l('Save Profile'))
