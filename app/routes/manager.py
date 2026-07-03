from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.vacation import VacationRequest
from app.models.department import Department
from app.forms.manager_forms import ApprovalForm
from app.services.vacation_service import count_working_days
from app.services.export_service import export_vacation_plan
from app.routes import manager_or_hr_required, log_audit

bp = Blueprint('manager', __name__, url_prefix='/manager')


def get_subordinate_ids(user):
    subordinates = User.query.filter_by(manager_id=user.id).all()
    return [u.id for u in subordinates]


@bp.route('/')
@login_required
@manager_or_hr_required
def dashboard():
    sub_ids = get_subordinate_ids(current_user)
    if current_user.is_hr or current_user.is_admin:
        pending = VacationRequest.query.filter_by(status='pending').order_by(VacationRequest.created_at.desc()).all()
    else:
        pending = VacationRequest.query.filter(
            VacationRequest.user_id.in_(sub_ids),
            VacationRequest.status == 'pending',
        ).order_by(VacationRequest.created_at.desc()).all()
    team_members = User.query.filter(User.id.in_(sub_ids)).all() if sub_ids else []
    change_requests = VacationRequest.query.filter(
        VacationRequest.user_id.in_(sub_ids) if sub_ids else db.false(),
        VacationRequest.change_status == 'pending',
    ).order_by(VacationRequest.updated_at.desc()).all() if sub_ids else []
    if current_user.is_hr or current_user.is_admin:
        change_requests = VacationRequest.query.filter_by(change_status='pending').order_by(VacationRequest.updated_at.desc()).all()
    return render_template('manager/dashboard.html', pending=pending, change_requests=change_requests, team_members=team_members)


@bp.route('/team')
@login_required
@manager_or_hr_required
def team():
    page = request.args.get('page', 1, type=int)
    sub_ids = get_subordinate_ids(current_user)
    if current_user.is_hr or current_user.is_admin:
        query = VacationRequest.query.filter(
            VacationRequest.status.in_(['approved', 'pending', 'hr_assigned']),
        )
    else:
        query = VacationRequest.query.filter(
            VacationRequest.user_id.in_(sub_ids),
        )
    requests = query.order_by(VacationRequest.start_date.desc()).paginate(page=page, per_page=20, error_out=False)
    team_members = User.query.filter(User.id.in_(sub_ids)).all() if sub_ids else []
    return render_template('manager/team.html', requests=requests, team_members=team_members)


@bp.route('/approve/<int:req_id>', methods=['GET', 'POST'])
@login_required
@manager_or_hr_required
def approve_request(req_id):
    req = db.session.get(VacationRequest, req_id)
    if not req:
        flash(_('Request not found.'), 'danger')
        return redirect(url_for('manager.dashboard'))
    sub_ids = get_subordinate_ids(current_user)
    if req.user_id not in sub_ids and not current_user.is_hr and not current_user.is_admin:
        flash(_('You are not authorized to approve this request.'), 'danger')
        return redirect(url_for('manager.dashboard'))
    if req.status != 'pending' and req.change_status != 'pending':
        flash(_('This request has already been processed.'), 'warning')
        return redirect(url_for('manager.dashboard'))
    form = ApprovalForm()
    if form.validate_on_submit():
        req.status = form.action.data
        req.approved_by = current_user.id
        req.approved_at = db.func.now()
        req.comment = form.comment.data or None
        db.session.commit()
        log_audit('approve_vacation', f'{form.action.data} vacation request #{req.id} for {req.user.username}')
        from app.services.notification_service import notify_vacation_approved, notify_vacation_rejected
        if form.action.data == 'approved':
            notify_vacation_approved(req, current_user)
        else:
            notify_vacation_rejected(req, current_user, form.comment.data)
        flash(_('Request %(action)s.', action=_(form.action.data.capitalize())), 'success')
        return redirect(url_for('manager.dashboard'))
    return render_template('manager/approve.html', form=form, req=req)


@bp.route('/change-response/<int:req_id>', methods=['POST'])
@login_required
@manager_or_hr_required
def change_response(req_id):
    req = db.session.get(VacationRequest, req_id)
    if not req:
        flash(_('Request not found.'), 'danger')
        return redirect(url_for('manager.dashboard'))
    sub_ids = get_subordinate_ids(current_user)
    if req.user_id not in sub_ids and not current_user.is_hr and not current_user.is_admin:
        flash(_('You are not authorized to respond to this change request.'), 'danger')
        return redirect(url_for('manager.dashboard'))
    if req.change_status != 'pending':
        flash(_('This change request has already been processed.'), 'warning')
        return redirect(url_for('manager.dashboard'))
    action = request.form.get('action')
    if action not in ('approved', 'rejected'):
        flash(_('Invalid action.'), 'danger')
        return redirect(url_for('manager.dashboard'))
    from app.services.notification_service import send_notification, send_email_notification, _with_locale
    if action == 'approved':
        req.start_date = req.change_requested_start
        req.end_date = req.change_requested_end
        req.days_count = count_working_days(req.change_requested_start, req.change_requested_end)
        req.change_requested_start = None
        req.change_requested_end = None
        req.change_reason = None
        req.change_status = None
        req.approved_by = current_user.id
        req.approved_at = db.func.now()
        db.session.commit()
        log_audit('approve_vacation_change', f'Approved change for vacation #{req.id}')
        notification_message = _('%(name)s changed your vacation from %(orig_start)s to %(orig_end)s.',
                                 name=req.user.display_name or req.user.username,
                                 orig_start=req.start_date.strftime('%d/%m/%Y'),
                                 orig_end=req.end_date.strftime('%d/%m/%Y'))
        send_notification(
            req.user_id,
            _('Change Request Approved'),
            notification_message,
            'success',
            link='/vacation/my-vacations'
        )
        if req.user.email:
            def _send_email():
                subject = _('Change Request Approved')
                body_html = render_template('emails/change_request_approved.html', request=req, approved_by=current_user, user=req.user)
                body_text = _('%(name)s approved your request to change your vacation from %(orig_start)s to %(orig_end)s.',
                              name=current_user.display_name or current_user.username,
                              orig_start=req.start_date.strftime('%d/%m/%Y'),
                              orig_end=req.end_date.strftime('%d/%m/%Y'))
                send_email_notification(req.user.email, subject, body_html, body_text)
            _with_locale(_send_email, req.user.email_locale if getattr(req.user, 'email_locale', None) else None)
        flash(_('Change request approved and vacation dates updated.'), 'success')
    else:
        req.change_requested_start = None
        req.change_requested_end = None
        req.change_reason = None
        req.change_status = 'rejected'
        db.session.commit()
        log_audit('reject_vacation_change', f'Rejected change for vacation #{req.id}')
        notification_message = _('Your request to change your vacation dates has been rejected.')
        send_notification(
            req.user_id,
            _('Change Request Rejected'),
            notification_message,
            'danger',
            link='/vacation/my-vacations'
        )
        if req.user.email:
            def _send_email():
                subject = _('Change Request Rejected')
                body_html = render_template('emails/change_request_rejected.html', request=req, rejected_by=current_user, user=req.user)
                body_text = _('Your request to change your vacation dates has been rejected.')
                send_email_notification(req.user.email, subject, body_html, body_text)
            _with_locale(_send_email, req.user.email_locale if getattr(req.user, 'email_locale', None) else None)
        flash(_('Change request rejected.'), 'success')
    return redirect(url_for('manager.dashboard'))


@bp.route('/export')
@login_required
@manager_or_hr_required
def export():
    if current_user.is_hr or current_user.is_admin:
        requests = VacationRequest.query.filter(
            VacationRequest.status.in_(['approved', 'hr_assigned']),
        ).order_by(VacationRequest.start_date.asc()).all()
    else:
        sub_ids = get_subordinate_ids(current_user)
        requests = VacationRequest.query.filter(
            VacationRequest.user_id.in_(sub_ids),
            VacationRequest.status.in_(['approved', 'hr_assigned']),
        ).order_by(VacationRequest.start_date.asc()).all()
    if not requests:
        flash(_('No approved vacations to export.'), 'warning')
        return redirect(url_for('manager.dashboard'))
    output = export_vacation_plan(requests)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='vacation_plan.xlsx',
    )
