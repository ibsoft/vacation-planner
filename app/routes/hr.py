from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.vacation import VacationRequest, VacationCause, VacationAssignment
from app.models.holiday import GreekHoliday
from app.models.department import Department
from app.forms.hr_forms import SetVacationDaysForm, AssignVacationForm
from app.services.vacation_service import count_working_days
from app.routes import hr_required, log_audit

bp = Blueprint('hr', __name__, url_prefix='/hr')


@bp.route('/')
@login_required
@hr_required
def dashboard():
    stats = {
        'total_users': User.query.filter_by(is_active=True).count(),
        'pending_all': VacationRequest.query.filter_by(status='pending').count(),
        'approved_this_month': VacationRequest.query.filter(
            VacationRequest.status.in_(['approved', 'hr_assigned']),
            db.extract('month', VacationRequest.created_at) == db.func.strftime('%m', db.func.now()),
            db.extract('year', VacationRequest.created_at) == db.func.strftime('%Y', db.func.now()),
        ).count(),
    }
    recent_requests = VacationRequest.query.order_by(VacationRequest.created_at.desc()).limit(10).all()
    return render_template('hr/dashboard.html', stats=stats, recent_requests=recent_requests)


@bp.route('/users')
@login_required
@hr_required
def users():
    page = request.args.get('page', 1, type=int)
    all_users = User.query.filter_by(is_active=True).order_by(User.username).paginate(page=page, per_page=20, error_out=False)
    return render_template('hr/users.html', users=all_users)


@bp.route('/users/<int:user_id>/set-days', methods=['GET', 'POST'])
@login_required
@hr_required
def set_vacation_days(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(_('User not found.'), 'danger')
        return redirect(url_for('hr.users'))
    form = SetVacationDaysForm()
    if form.validate_on_submit():
        user.vacation_days_per_year = form.vacation_days_per_year.data
        db.session.commit()
        log_audit('set_vacation_days', f'Set vacation days for {user.username} to {form.vacation_days_per_year.data}')
        flash(_('Vacation days updated for %(name)s.', name=user.display_name or user.username), 'success')
        return redirect(url_for('hr.users'))
    form.vacation_days_per_year.data = user.vacation_days_per_year
    return render_template('hr/set_vacation_days.html', form=form, user=user)


@bp.route('/assign', methods=['GET', 'POST'])
@login_required
@hr_required
def assign_vacation():
    form = AssignVacationForm()
    holiday_dates = [h.date.isoformat() for h in GreekHoliday.query.with_entities(GreekHoliday.date).all()]
    form.user_id.choices = [(u.id, f'{u.display_name or u.username}') for u in User.query.filter_by(is_active=True).order_by(User.username).all()]
    form.cause_id.choices = [(c.id, c.name) for c in VacationCause.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        user = db.session.get(User, form.user_id.data)
        cause = db.session.get(VacationCause, form.cause_id.data)
        if not user or not cause:
            flash(_('Invalid selection.'), 'danger')
            return render_template('hr/assign_vacation.html', form=form, holiday_dates=holiday_dates)
        days_count = count_working_days(form.start_date.data, form.end_date.data)
        if days_count == 0:
            flash(_('Selected range has no working days.'), 'warning')
            return render_template('hr/assign_vacation.html', form=form, holiday_dates=holiday_dates)
        if user.remaining_days < days_count:
            flash(_('User does not have enough remaining vacation days.'), 'danger')
            return render_template('hr/assign_vacation.html', form=form, holiday_dates=holiday_dates)
        req = VacationRequest(
            user_id=user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            days_count=days_count,
            reason=form.reason.data or cause.name,
            status='approved',
            request_type='hr_assigned',
            cause_id=cause.id,
            approved_by=current_user.id,
            approved_at=db.func.now(),
        )
        db.session.add(req)
        db.session.commit()
        log_audit('hr_assign_vacation', f'HR assigned vacation to {user.username}: {form.start_date.data} to {form.end_date.data}, cause: {cause.name}')
        from app.services.notification_service import notify_hr_assigned
        notify_hr_assigned(req, current_user)
        flash(_('Vacation assigned to %(name)s successfully.', name=user.display_name or user.username), 'success')
        return redirect(url_for('hr.dashboard'))
    return render_template('hr/assign_vacation.html', form=form, holiday_dates=holiday_dates)


@bp.route('/all')
@login_required
@hr_required
def all_vacations():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    department_id = request.args.get('department', 0, type=int)
    query = VacationRequest.query.join(VacationRequest.user)
    if q:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{q}%'),
                VacationRequest.status.ilike(f'%{q}%'),
            )
        )
    if status_filter:
        query = query.filter(VacationRequest.status == status_filter)
    if department_id:
        query = query.filter(User.department_id == department_id)
    requests = query.order_by(VacationRequest.start_date.desc()).paginate(page=page, per_page=20, error_out=False)
    departments = Department.query.order_by(Department.name).all()
    return render_template('hr/all_vacations.html', requests=requests, departments=departments,
                           status_filter=status_filter, department_id=department_id)
