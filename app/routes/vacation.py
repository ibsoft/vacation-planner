from datetime import timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.vacation import VacationRequest, VacationCause
from app.models.holiday import GreekHoliday
from app.models.department import Department
from app.forms.vacation_forms import VacationRequestForm, ChangeRequestForm, VacationEditForm
from app.services.vacation_service import count_working_days
from app.routes import log_audit

bp = Blueprint('vacation', __name__)


@bp.route('/')
@login_required
def dashboard():
    now = db.func.now()
    upcoming = VacationRequest.query.filter(
        VacationRequest.user_id == current_user.id,
        VacationRequest.status.in_(['approved', 'pending', 'hr_assigned']),
        VacationRequest.end_date >= db.func.date(now),
    ).order_by(VacationRequest.start_date.asc()).all()
    past = VacationRequest.query.filter(
        VacationRequest.user_id == current_user.id,
        VacationRequest.end_date < db.func.date(now),
    ).order_by(VacationRequest.start_date.desc()).limit(10).all()
    team_vacations = []
    if current_user.manager_id or current_user.is_manager:
        subordinates = User.query.filter_by(manager_id=current_user.id).all()
        sub_ids = [u.id for u in subordinates]
        if sub_ids:
            team_vacations = VacationRequest.query.filter(
                VacationRequest.user_id.in_(sub_ids),
                VacationRequest.status.in_(['approved', 'pending', 'hr_assigned']),
                VacationRequest.end_date >= db.func.date(now),
            ).order_by(VacationRequest.start_date.asc()).all()
    return render_template('vacation/dashboard.html',
                           upcoming=upcoming, past=past,
                           team_vacations=team_vacations,
                           remaining=current_user.remaining_days,
                           total=current_user.vacation_days_per_year)


@bp.route('/vacation/new', methods=['GET', 'POST'])
@login_required
def new_request():
    form = VacationRequestForm()
    causes = VacationCause.query.filter_by(is_active=True).order_by(VacationCause.name).all()
    form.cause_id.choices = [(c.id, c.name) for c in causes] + [(-1, _('Other (write custom)'))]
    holiday_dates = [h.date.isoformat() for h in GreekHoliday.query.with_entities(GreekHoliday.date).all()]
    if form.is_submitted() and not form.validate():
        flash(_('Please fix the errors below.'), 'danger')
    if form.validate_on_submit():
        if form.start_date.data > form.end_date.data:
            flash(_('End date must be after start date.'), 'danger')
            return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)
        days_count = count_working_days(form.start_date.data, form.end_date.data)
        if days_count == 0:
            flash(_('Selected range has no working days (weekends/holidays).'), 'warning')
            return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)
        if current_user.remaining_days < days_count:
            flash(_('Insufficient vacation days remaining.'), 'danger')
            return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)
        overlap = VacationRequest.query.filter(
            VacationRequest.user_id == current_user.id,
            VacationRequest.status.in_(['pending', 'approved', 'hr_assigned']),
            VacationRequest.start_date <= form.end_date.data,
            VacationRequest.end_date >= form.start_date.data,
        ).first()
        if overlap:
            flash(_('You already have a vacation request overlapping these dates.'), 'danger')
            return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)
        if form.cause_id.data == -1:
            if not form.custom_reason.data or not form.custom_reason.data.strip():
                flash(_('Please provide a custom reason.'), 'danger')
                return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)
            reason_text = form.custom_reason.data.strip()
            cause_id = None
        else:
            reason_text = VacationCause.query.get(form.cause_id.data).name
            cause_id = form.cause_id.data
        req = VacationRequest(
            user_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            days_count=days_count,
            reason=reason_text,
            cause_id=cause_id,
            status='pending',
        )
        db.session.add(req)
        db.session.commit()
        log_audit('create_vacation_request', f'Created vacation request: {form.start_date.data} to {form.end_date.data} ({days_count} days)')
        from app.services.notification_service import notify_vacation_created
        notify_vacation_created(req)
        flash(_('Vacation request submitted for approval.'), 'success')
        return redirect(url_for('vacation.dashboard'))
    return render_template('vacation/new_request.html', form=form, holiday_dates=holiday_dates)


@bp.route('/vacation/my-vacations')
@login_required
def my_vacations():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = VacationRequest.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter(VacationRequest.status == status_filter)
    requests = query.order_by(VacationRequest.start_date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('vacation/my_vacations.html', requests=requests, status_filter=status_filter)


@bp.route('/vacation/<int:req_id>/cancel', methods=['POST'])
@login_required
def cancel_request(req_id):
    req = db.session.get(VacationRequest, req_id)
    if not req or req.user_id != current_user.id:
        flash(_('Request not found.'), 'danger')
        return redirect(url_for('vacation.my_vacations'))
    if req.status != 'pending':
        flash(_('Only pending requests can be cancelled.'), 'warning')
        return redirect(url_for('vacation.my_vacations'))
    req.status = 'cancelled'
    db.session.commit()
    log_audit('cancel_vacation_request', f'Cancelled vacation request #{req.id}')
    from app.services.notification_service import notify_vacation_cancelled
    notify_vacation_cancelled(req)
    flash(_('Vacation request cancelled.'), 'success')
    return redirect(url_for('vacation.my_vacations'))


@bp.route('/vacation/<int:req_id>/change', methods=['GET', 'POST'])
@login_required
def change_request(req_id):
    req = db.session.get(VacationRequest, req_id)
    if not req or req.user_id != current_user.id:
        flash(_('Request not found.'), 'danger')
        return redirect(url_for('vacation.my_vacations'))
    if req.status not in ('pending', 'approved'):
        flash(_('Only pending or approved vacations can be changed.'), 'warning')
        return redirect(url_for('vacation.my_vacations'))
    if req.request_type == 'hr_assigned':
        flash(_('HR-assigned vacations cannot be changed.'), 'warning')
        return redirect(url_for('vacation.my_vacations'))
    form = ChangeRequestForm()
    if form.validate_on_submit():
        if form.start_date.data > form.end_date.data:
            flash(_('End date must be after start date.'), 'danger')
            return render_template('vacation/change_request.html', form=form, req=req)
        days_count = count_working_days(form.start_date.data, form.end_date.data)
        if days_count == 0:
            flash(_('Selected range has no working days (weekends/holidays).'), 'warning')
            return render_template('vacation/change_request.html', form=form, req=req)
        if current_user.remaining_days + req.days_count < days_count:
            flash(_('Insufficient vacation days remaining.'), 'danger')
            return render_template('vacation/change_request.html', form=form, req=req)
        overlap = VacationRequest.query.filter(
            VacationRequest.user_id == current_user.id,
            VacationRequest.id != req.id,
            VacationRequest.status.in_(['pending', 'approved', 'hr_assigned']),
            VacationRequest.start_date <= form.end_date.data,
            VacationRequest.end_date >= form.start_date.data,
        ).first()
        if overlap:
            flash(_('You already have a vacation request overlapping these dates.'), 'danger')
            return render_template('vacation/change_request.html', form=form, req=req)
        req.change_requested_start = form.start_date.data
        req.change_requested_end = form.end_date.data
        req.change_reason = form.change_reason.data
        req.change_status = 'pending'
        db.session.commit()
        log_audit('vacation_change_request', f'Change requested for vacation #{req.id}: {form.start_date.data} to {form.end_date.data}')
        from app.services.notification_service import send_notification
        manager = current_user.manager
        if manager:
            send_notification(
                manager.id,
                _('Vacation Change Request'),
                _('%(name)s requested a change to their vacation from %(orig_start)s to %(orig_end)s: new dates %(new_start)s to %(new_end)s.',
                  name=current_user.display_name or current_user.username,
                  orig_start=req.start_date.strftime('%d/%m/%Y'),
                  orig_end=req.end_date.strftime('%d/%m/%Y'),
                  new_start=form.start_date.data.strftime('%d/%m/%Y'),
                  new_end=form.end_date.data.strftime('%d/%m/%Y')),
                'info',
                link=f'/manager/approve/{req.id}'
            )
        flash(_('Change request submitted for approval.'), 'success')
        return redirect(url_for('vacation.my_vacations'))
    return render_template('vacation/change_request.html', form=form, req=req)


@bp.route('/vacation/<int:req_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_request(req_id):
    req = db.session.get(VacationRequest, req_id)
    if not req:
        flash(_('Request not found.'), 'danger')
        return redirect(url_for('vacation.my_vacations'))

    user = req.user
    is_owner = current_user.id == req.user_id
    is_hr = current_user.is_hr or current_user.is_admin
    is_manager = current_user.id == user.manager_id

    can_edit = False
    if is_owner and req.status == 'pending':
        can_edit = True
    elif is_hr and req.status in ('pending', 'approved'):
        can_edit = True
    elif is_manager and req.status in ('pending', 'approved'):
        can_edit = True

    if not can_edit:
        flash(_('You are not allowed to edit this request.'), 'danger')
        return redirect(url_for('vacation.my_vacations'))

    holiday_dates = [h.date.isoformat() for h in GreekHoliday.query.with_entities(GreekHoliday.date).all()]
    form = VacationEditForm()

    if form.is_submitted() and not form.validate():
        flash(_('Please fix the errors below.'), 'danger')

    if form.validate_on_submit():
        if form.start_date.data > form.end_date.data:
            flash(_('End date must be after start date.'), 'danger')
            return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)

        days_count = count_working_days(form.start_date.data, form.end_date.data)
        if days_count == 0:
            flash(_('Selected range has no working days (weekends/holidays).'), 'warning')
            return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)

        if req.status == 'approved':
            if current_user.remaining_days + req.days_count < days_count:
                flash(_('Insufficient vacation days remaining.'), 'danger')
                return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)
        else:
            if current_user.remaining_days < days_count:
                flash(_('Insufficient vacation days remaining.'), 'danger')
                return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)

        overlap = VacationRequest.query.filter(
            VacationRequest.user_id == req.user_id,
            VacationRequest.id != req.id,
            VacationRequest.status.in_(['pending', 'approved', 'hr_assigned']),
            VacationRequest.start_date <= form.end_date.data,
            VacationRequest.end_date >= form.start_date.data,
        ).first()
        if overlap:
            flash(_('This period overlaps with an existing vacation request.'), 'danger')
            return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)

        old_start = req.start_date
        old_end = req.end_date
        old_days = req.days_count

        req.start_date = form.start_date.data
        req.end_date = form.end_date.data
        req.days_count = days_count
        db.session.commit()

        log_audit('edit_vacation_dates',
                  f'Edited vacation #{req.id}: {old_start.strftime("%d/%m/%Y")}–{old_end.strftime("%d/%m/%Y")} '
                  f'({old_days} days) → {form.start_date.data.strftime("%d/%m/%Y")}–{form.end_date.data.strftime("%d/%m/%Y")} '
                  f'({days_count} days) by {current_user.display_name or current_user.username}')

        from app.services.notification_service import send_notification
        if is_owner:
            manager = user.manager
            if manager:
                send_notification(
                    manager.id,
                    _('Vacation Dates Edited'),
                    _('%(name)s edited their vacation request #%(req_id)s from %(old_start)s–%(old_end)s to %(new_start)s–%(new_end)s.',
                      name=user.display_name or user.username,
                      req_id=req.id,
                      old_start=old_start.strftime('%d/%m/%Y'),
                      old_end=old_end.strftime('%d/%m/%Y'),
                      new_start=form.start_date.data.strftime('%d/%m/%Y'),
                      new_end=form.end_date.data.strftime('%d/%m/%Y')),
                    'info',
                    link=f'/manager/approve/{req.id}'
                )
        else:
            send_notification(
                req.user_id,
                _('Vacation Dates Edited'),
                _('Your vacation request #%(req_id)s has been edited by %(editor)s from %(old_start)s–%(old_end)s to %(new_start)s–%(new_end)s.',
                  req_id=req.id,
                  editor=current_user.display_name or current_user.username,
                  old_start=old_start.strftime('%d/%m/%Y'),
                  old_end=old_end.strftime('%d/%m/%Y'),
                  new_start=form.start_date.data.strftime('%d/%m/%Y'),
                  new_end=form.end_date.data.strftime('%d/%m/%Y')),
                'info',
                link='/vacation/my-vacations'
            )

        flash(_('Vacation dates updated successfully.'), 'success')
        if is_owner:
            return redirect(url_for('vacation.my_vacations'))
        else:
            return redirect(url_for('hr.all_vacations'))

    if request.method == 'GET':
        form.start_date.data = req.start_date
        form.end_date.data = req.end_date

    return render_template('vacation/edit_request.html', form=form, req=req, holiday_dates=holiday_dates)


@bp.route('/team')
@login_required
def team_calendar():
    department_id = request.args.get('department', 0, type=int)
    if department_id == 0 and current_user.department_id:
        department_id = current_user.department_id
    query = User.query
    if department_id:
        query = query.filter_by(department_id=department_id)
    else:
        query = query.filter(User.department_id.isnot(None))

    if not current_user.is_hr and not current_user.is_admin:
        if current_user.is_top_management:
            pass
        elif current_user.manager_id:
            query = query.filter(
                db.or_(
                    User.department_id == current_user.department_id,
                    User.manager_id == current_user.id,
                )
            )
        else:
            query = query.filter(User.department_id == current_user.department_id)

    team_members = query.all()
    member_ids = [u.id for u in team_members]

    vacations = VacationRequest.query.filter(
        VacationRequest.user_id.in_(member_ids),
        VacationRequest.status.in_(['approved', 'pending', 'hr_assigned']),
    ).order_by(VacationRequest.start_date.asc()).all()

    holidays = GreekHoliday.query.filter(
        db.extract('year', GreekHoliday.date) == db.func.strftime('%Y', db.func.now())
    ).all()

    departments = Department.query.order_by(Department.name).all()

    def user_color(user_id):
        hue = (user_id * 137.508) % 360
        return f'hsl({hue:.0f}, 65%, 55%)'

    events = []
    for vac in vacations:
        title = vac.user.display_name or vac.user.username
        if vac.request_type == 'hr_assigned' and vac.cause:
            title += f' ({vac.cause.name})'
        avatar = vac.user.avatar_url or vac.user.gravatar_url
        events.append({
            'id': str(vac.id),
            'title': title,
            'start': vac.start_date.isoformat(),
            'end': (vac.end_date + timedelta(days=1)).isoformat(),
            'color': user_color(vac.user_id),
            'textColor': '#fff',
            'extendedProps': {
                'status': vac.status,
                'type': vac.request_type,
                'days': vac.days_count,
                'username': vac.user.display_name or vac.user.username,
                'department': vac.user.department.name if vac.user.department else '',
                'avatar_url': avatar,
            }
        })

    for h in holidays:
        events.append({
            'id': f'holiday-{h.id}',
            'title': h.name,
            'start': h.date.isoformat(),
            'end': h.date.isoformat(),
            'color': '#dc3545',
            'textColor': '#fff',
            'display': 'background',
            'extendedProps': {
                'status': 'holiday',
                'type': 'holiday',
            }
        })

    return render_template('vacation/team_calendar.html',
                           events=events,
                           departments=departments, department_id=department_id)
