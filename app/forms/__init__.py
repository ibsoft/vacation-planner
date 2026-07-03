from app.forms.auth_forms import LoginForm
from app.forms.admin_forms import UserForm, DepartmentForm, LdapSettingsForm, VacationCauseForm, HolidayForm, AdImportForm
from app.forms.hr_forms import SetVacationDaysForm, AssignVacationForm
from app.forms.vacation_forms import VacationRequestForm, ChangeRequestForm
from app.forms.manager_forms import ApprovalForm

__all__ = [
    'LoginForm', 'UserForm', 'DepartmentForm', 'LdapSettingsForm',
    'VacationCauseForm', 'HolidayForm', 'AdImportForm',
    'SetVacationDaysForm', 'AssignVacationForm',
    'VacationRequestForm', 'ChangeRequestForm', 'ApprovalForm',
]
