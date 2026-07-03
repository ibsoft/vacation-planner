from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SelectField, SubmitField, DateField, HiddenField
from wtforms.validators import DataRequired, Optional, Email, NumberRange
from flask_babel import lazy_gettext as _l


class UserForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[Optional(), Email()])
    display_name = StringField(_l('Display Name'))
    password = PasswordField(_l('Password'))
    is_admin = BooleanField(_l('Admin'))
    is_hr = BooleanField(_l('HR'))
    is_top_management = BooleanField(_l('Top Management'))
    is_active = BooleanField(_l('Active'))
    department_id = SelectField(_l('Department'), coerce=int, validators=[Optional()])
    manager_id = SelectField(_l('Manager'), coerce=int, validators=[Optional()])
    vacation_days_per_year = IntegerField(_l('Vacation Days/Year'), default=20, validators=[NumberRange(min=0, max=365)])
    locale = SelectField(_l('Language'), choices=[('en', 'English'), ('el', 'Ελληνικά')], default='en')
    submit = SubmitField(_l('Save'))


class DepartmentForm(FlaskForm):
    name = StringField(_l('Name (English)'), validators=[DataRequired()])
    name_el = StringField(_l('Name (Greek)'))
    manager_id = SelectField(_l('Department Manager'), coerce=int, validators=[Optional()])
    submit = SubmitField(_l('Save'))


class LdapSettingsForm(FlaskForm):
    ldap_server = StringField(_l('LDAP Server'), validators=[DataRequired()])
    ldap_base_dn = StringField(_l('Base DN'), validators=[DataRequired()])
    ldap_bind_dn = StringField(_l('Bind DN'), validators=[DataRequired()])
    ldap_bind_password = PasswordField(_l('Bind Password'))
    ldap_user_filter = StringField(_l('User Filter'), default='(&(objectClass=user)(objectCategory=person))')
    ldap_username_attr = StringField(_l('Username Attribute'), default='sAMAccountName')
    ldap_email_attr = StringField(_l('Email Attribute'), default='mail')
    ldap_dept_attr = StringField(_l('Department Attribute'), default='department')
    ldap_manager_attr = StringField(_l('Manager Attribute'), default='manager')
    ldap_display_name_attr = StringField(_l('Display Name Attribute'), default='displayName')
    submit = SubmitField(_l('Save Settings'))


class VacationCauseForm(FlaskForm):
    name = StringField(_l('Name (English)'), validators=[DataRequired()])
    name_el = StringField(_l('Name (Greek)'))
    is_active = BooleanField(_l('Active'), default=True)
    submit = SubmitField(_l('Save'))


class HolidayForm(FlaskForm):
    date = DateField(_l('Date'), validators=[DataRequired()])
    name = StringField(_l('Name (English)'), validators=[DataRequired()])
    name_el = StringField(_l('Name (Greek)'))
    submit = SubmitField(_l('Save'))


class EmailSettingsForm(FlaskForm):
    smtp_server = StringField(_l('SMTP Server'), validators=[Optional()])
    smtp_port = IntegerField(_l('SMTP Port'), default=587, validators=[Optional()])
    smtp_user = StringField(_l('SMTP Username'), validators=[Optional()])
    smtp_password = PasswordField(_l('SMTP Password'))
    smtp_from = StringField(_l('From Email'), validators=[Optional()])
    smtp_use_tls = BooleanField(_l('Use TLS'), default=True)
    smtp_no_auth = BooleanField(_l('No Authentication (anonymous SMTP)'), default=False)
    smtp_text_only = BooleanField(_l('Text Only (plain text, no HTML)'), default=False)
    email_locale = SelectField(_l('Email Language'), choices=[('en', 'English'), ('el', 'Ελληνικά')], default='en')
    submit = SubmitField(_l('Save Settings'))


class AdImportForm(FlaskForm):
    preview_data = HiddenField()
    submit = SubmitField(_l('Import Users'))


class HolidayImportForm(FlaskForm):
    csv_file = FileField(_l('CSV File'), validators=[DataRequired()])
    submit = SubmitField(_l('Import'))
