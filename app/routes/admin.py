import csv
from datetime import datetime

import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.models.vacation import VacationRequest, VacationCause, VacationAssignment
from app.models.holiday import GreekHoliday
from app.models.setting import LdapSetting, EmailSetting
from app.models.audit import AuditLog
from app.forms.admin_forms import UserForm, DepartmentForm, LdapSettingsForm, VacationCauseForm, HolidayForm, HolidayImportForm, EmailSettingsForm
from app.services.ldap_service import search_users
from app.routes import admin_required, log_audit

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@login_required
@admin_required
def dashboard():
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_departments': Department.query.count(),
        'pending_requests': VacationRequest.query.filter_by(status='pending').count(),
        'approved_this_month': VacationRequest.query.filter(
            VacationRequest.status.in_(['approved', 'hr_assigned']),
            db.extract('month', VacationRequest.created_at) == db.extract('month', db.func.now()),
            db.extract('year', VacationRequest.created_at) == db.extract('year', db.func.now()),
        ).count(),
        'total_holidays': GreekHoliday.query.count(),
        'active_causes': VacationCause.query.filter_by(is_active=True).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


@bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = User.query
    if q:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{q}%'),
                User.display_name.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%'),
            )
        )
    all_users = query.order_by(User.username).paginate(page=page, per_page=20, error_out=False)
    departments = Department.query.all()
    return render_template('admin/users.html', users=all_users, departments=departments)


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def user_new():
    form = UserForm()
    form.department_id.choices = [(0, _('None'))] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.manager_id.choices = [(0, _('None'))] + [(u.id, f'{u.display_name or u.username}') for u in User.query.order_by(User.username).all()]
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash(_('Username already exists.'), 'danger')
            return render_template('admin/user_form.html', form=form, title=_('New User'))
        user = User(
            username=form.username.data,
            email=form.email.data or None,
            display_name=form.display_name.data or None,
            is_admin=form.is_admin.data,
            is_hr=form.is_hr.data,
            is_top_management=form.is_top_management.data,
            is_active=form.is_active.data,
            department_id=form.department_id.data if form.department_id.data and form.department_id.data != 0 else None,
            manager_id=form.manager_id.data if form.manager_id.data and form.manager_id.data != 0 else None,
            vacation_days_per_year=form.vacation_days_per_year.data,
            locale=form.locale.data,
            email_locale=form.email_locale.data or None,
        )
        if form.password.data:
            user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        log_audit('create_user', f'Created user {user.username}')
        flash(_('User created successfully.'), 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title=_('New User'))


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(_('User not found.'), 'danger')
        return redirect(url_for('admin.users'))
    form = UserForm(obj=user)
    form.department_id.choices = [(0, _('None'))] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.manager_id.choices = [(0, _('None'))] + [(u.id, f'{u.display_name or u.username}') for u in User.query.order_by(User.username).all() if u.id != user.id]
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data or None
        user.display_name = form.display_name.data or None
        user.is_admin = form.is_admin.data
        user.is_hr = form.is_hr.data
        user.is_top_management = form.is_top_management.data
        user.is_active = form.is_active.data
        user.department_id = form.department_id.data if form.department_id.data and form.department_id.data != 0 else None
        user.manager_id = form.manager_id.data if form.manager_id.data and form.manager_id.data != 0 else None
        user.vacation_days_per_year = form.vacation_days_per_year.data
        user.locale = form.locale.data
        user.email_locale = form.email_locale.data or None
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        log_audit('edit_user', f'Edited user {user.username}')
        flash(_('User updated successfully.'), 'success')
        return redirect(url_for('admin.users'))
    form.department_id.data = user.department_id or 0
    form.manager_id.data = user.manager_id or 0
    form.email_locale.data = user.email_locale or ''
    return render_template('admin/user_form.html', form=form, user=user, title=_('Edit User'))


@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def user_toggle_active(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(_('User not found.'), 'danger')
        return redirect(url_for('admin.users'))
    if user.id == current_user.id:
        flash(_('You cannot disable yourself.'), 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    log_audit('toggle_user_active', f'{"" if user.is_active else "De"}activated user {user.username}')
    flash(_('User %(name)s %(status)s.', name=user.username, status=_('activated') if user.is_active else _('deactivated')), 'success')
    return redirect(url_for('admin.users'))


@bp.route('/departments')
@login_required
@admin_required
def departments():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = Department.query
    if q:
        query = query.filter(Department.name.ilike(f'%{q}%'))
    all_depts = query.order_by(Department.name).paginate(page=page, per_page=20, error_out=False)
    all_users = User.query.order_by(User.username).all()
    return render_template('admin/departments.html', departments=all_depts, users=all_users)


@bp.route('/departments/new', methods=['GET', 'POST'])
@login_required
@admin_required
def department_new():
    form = DepartmentForm()
    form.manager_id.choices = [(0, _('None'))] + [(u.id, f'{u.display_name or u.username}') for u in User.query.order_by(User.username).all()]
    if form.validate_on_submit():
        dept = Department(name=form.name.data, name_el=form.name_el.data or None)
        db.session.add(dept)
        db.session.flush()
        if form.manager_id.data and form.manager_id.data != 0:
            dept.manager_id = form.manager_id.data
        db.session.commit()
        log_audit('create_department', f'Created department {dept.name}')
        flash(_('Department created successfully.'), 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title=_('New Department'))


@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def department_edit(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept:
        flash(_('Department not found.'), 'danger')
        return redirect(url_for('admin.departments'))
    form = DepartmentForm(obj=dept)
    form.manager_id.choices = [(0, _('None'))] + [(u.id, f'{u.display_name or u.username}') for u in User.query.order_by(User.username).all()]
    if form.validate_on_submit():
        dept.name = form.name.data
        dept.name_el = form.name_el.data or None
        dept.manager_id = form.manager_id.data if form.manager_id.data and form.manager_id.data != 0 else None
        db.session.commit()
        log_audit('edit_department', f'Edited department {dept.name}')
        flash(_('Department updated successfully.'), 'success')
        return redirect(url_for('admin.departments'))
    form.manager_id.data = dept.manager_id or 0
    return render_template('admin/department_form.html', form=form, dept=dept, title=_('Edit Department'))


@bp.route('/ad-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def ad_settings():
    form = LdapSettingsForm()
    if form.validate_on_submit():
        for key in ['LDAP_SERVER', 'LDAP_BASE_DN', 'LDAP_BIND_DN', 'LDAP_USER_FILTER',
                     'LDAP_USERNAME_ATTR', 'LDAP_EMAIL_ATTR', 'LDAP_DEPT_ATTR',
                     'LDAP_MANAGER_ATTR', 'LDAP_DISPLAY_NAME_ATTR']:
            current_app.config[key] = getattr(form, key.lower()).data
            LdapSetting.set(key, getattr(form, key.lower()).data)
        if form.ldap_bind_password.data:
            current_app.config['LDAP_BIND_PASSWORD'] = form.ldap_bind_password.data
            LdapSetting.set('LDAP_BIND_PASSWORD', form.ldap_bind_password.data)
        db.session.commit()
        log_audit('update_ad_settings', 'Updated LDAP settings')
        flash(_('LDAP settings saved successfully.'), 'success')
        return redirect(url_for('admin.ad_settings'))
    LDAP_KEYS = {
        'ldap_server': ('LDAP_SERVER', ''),
        'ldap_base_dn': ('LDAP_BASE_DN', ''),
        'ldap_bind_dn': ('LDAP_BIND_DN', ''),
        'ldap_bind_password': ('LDAP_BIND_PASSWORD', ''),
        'ldap_user_filter': ('LDAP_USER_FILTER', '(&(objectClass=user)(objectCategory=person))'),
        'ldap_username_attr': ('LDAP_USERNAME_ATTR', 'sAMAccountName'),
        'ldap_email_attr': ('LDAP_EMAIL_ATTR', 'mail'),
        'ldap_dept_attr': ('LDAP_DEPT_ATTR', 'department'),
        'ldap_manager_attr': ('LDAP_MANAGER_ATTR', 'manager'),
        'ldap_display_name_attr': ('LDAP_DISPLAY_NAME_ATTR', 'displayName'),
    }
    for attr, (config_key, default) in LDAP_KEYS.items():
        db_val = LdapSetting.get(config_key, default)
        current_app.config[config_key] = db_val
        getattr(form, attr).data = db_val
    return render_template('admin/ad_settings.html', form=form)


@bp.route('/email-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def email_settings():
    form = EmailSettingsForm()
    if form.validate_on_submit():
        for key in ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_FROM', 'EMAIL_LOCALE']:
            current_app.config[key] = getattr(form, key.lower()).data
            EmailSetting.set(key, str(getattr(form, key.lower()).data or ''))
        if form.smtp_password.data:
            current_app.config['SMTP_PASSWORD'] = form.smtp_password.data
            EmailSetting.set('SMTP_PASSWORD', form.smtp_password.data)
        current_app.config['SMTP_USE_TLS'] = form.smtp_use_tls.data
        EmailSetting.set('SMTP_USE_TLS', '1' if form.smtp_use_tls.data else '0')
        current_app.config['SMTP_NO_AUTH'] = form.smtp_no_auth.data
        EmailSetting.set('SMTP_NO_AUTH', '1' if form.smtp_no_auth.data else '0')
        if form.smtp_no_auth.data:
            current_app.config['SMTP_USER'] = ''
            EmailSetting.set('SMTP_USER', '')
            current_app.config['SMTP_PASSWORD'] = ''
            EmailSetting.set('SMTP_PASSWORD', '')
        current_app.config['SMTP_TEXT_ONLY'] = form.smtp_text_only.data
        EmailSetting.set('SMTP_TEXT_ONLY', '1' if form.smtp_text_only.data else '0')
        db.session.commit()
        log_audit('update_email_settings', 'Updated email settings')
        flash(_('Email settings saved successfully.'), 'success')
        return redirect(url_for('admin.email_settings'))
    EMAIL_KEYS = {
        'smtp_server': ('SMTP_SERVER', ''),
        'smtp_port': ('SMTP_PORT', '587'),
        'smtp_user': ('SMTP_USER', ''),
        'smtp_password': ('SMTP_PASSWORD', ''),
        'smtp_from': ('SMTP_FROM', ''),
        'smtp_use_tls': ('SMTP_USE_TLS', '1'),
        'smtp_no_auth': ('SMTP_NO_AUTH', '0'),
        'smtp_text_only': ('SMTP_TEXT_ONLY', '0'),
        'email_locale': ('EMAIL_LOCALE', 'en'),
    }
    for attr, (config_key, default) in EMAIL_KEYS.items():
        db_val = EmailSetting.get(config_key, default)
        current_app.config[config_key] = db_val
        if attr in ('smtp_use_tls', 'smtp_no_auth', 'smtp_text_only'):
            getattr(form, attr).data = db_val == '1'
        else:
            getattr(form, attr).data = db_val
    return render_template('admin/email_settings.html', form=form)


@bp.route('/email-test', methods=['POST'])
@login_required
@admin_required
def email_test():
    from app.services.notification_service import send_email_notification
    try:
        send_email_notification(
            current_user.email,
            _('Test Email from Vacation Planner'),
            _('This is a test email to verify SMTP configuration.')
        )
        flash(_('Test email sent to %(email)s.', email=current_user.email), 'success')
    except Exception as e:
        flash(_('Failed to send test email: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.email_settings'))


@bp.route('/ad-test-connection', methods=['POST'])
@login_required
@admin_required
def ad_test_connection():
    from app.services.ldap_service import get_ldap_connection
    try:
        conn = get_ldap_connection()
        if conn.bound:
            flash(_('LDAP connection successful!'), 'success')
        else:
            flash(_('LDAP connection failed.'), 'danger')
    except Exception as e:
        flash(_('LDAP connection error: %(error)s', error=str(e)), 'danger')
    return redirect(url_for('admin.ad_settings'))


@bp.route('/ad-import', methods=['GET', 'POST'])
@login_required
@admin_required
def ad_import():
    imported_users = []
    if request.method == 'POST' and 'preview' in request.form:
        try:
            imported_users = search_users()
            session['ad_preview'] = imported_users
            if not imported_users:
                flash(_('No users found in Active Directory. Check your LDAP settings.'), 'warning')
        except Exception as e:
            flash(_('LDAP connection error: %(error)s', error=str(e)), 'danger')
    elif request.method == 'POST' and 'import_selected' in request.form:
        selected_dns = request.form.getlist('selected_users')
        preview_users = session.get('ad_preview', [])
        if not selected_dns:
            flash(_('No users selected. Please check the users you want to import.'), 'warning')
            imported_users = preview_users
        else:
            imported_count = 0
            updated_count = 0
            for ad_user in preview_users:
                if ad_user.get('dn') not in selected_dns:
                    continue
                username = ad_user['username']
                existing = User.query.filter_by(username=username).first()
                if not existing:
                    user = User(
                        username=username,
                        email=ad_user.get('email') or None,
                        display_name=ad_user.get('display_name') or None,
                        ad_guid=ad_user.get('guid') or None,
                        ad_dn=ad_user.get('dn') or None,
                        is_active=True,
                    )
                    db.session.add(user)
                    imported_count += 1
                else:
                    existing.ad_dn = ad_user.get('dn') or existing.ad_dn
                    existing.ad_guid = ad_user.get('guid') or existing.ad_guid
                    if ad_user.get('email'):
                        existing.email = ad_user.get('email')
                    if ad_user.get('display_name'):
                        existing.display_name = ad_user.get('display_name')
                    updated_count += 1
            db.session.commit()
            log_audit('ad_import', f'Imported {imported_count} new, updated {updated_count} users from AD')
            flash(_('Import complete: %(new)s new users added, %(up)s updated.', new=imported_count, up=updated_count), 'success')
            session.pop('ad_preview', None)
            return redirect(url_for('admin.users'))
    else:
        imported_users = session.get('ad_preview', [])
    all_users = User.query.all()
    return render_template('admin/ad_import.html', imported_users=imported_users, users=all_users)


@bp.route('/causes')
@login_required
@admin_required
def causes():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = VacationCause.query
    if q:
        query = query.filter(VacationCause.name.ilike(f'%{q}%'))
    all_causes = query.order_by(VacationCause.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/causes.html', causes=all_causes)


@bp.route('/causes/new', methods=['GET', 'POST'])
@login_required
@admin_required
def cause_new():
    form = VacationCauseForm()
    if form.validate_on_submit():
        cause = VacationCause(
            name=form.name.data,
            name_el=form.name_el.data or None,
            is_active=form.is_active.data,
        )
        db.session.add(cause)
        db.session.commit()
        log_audit('create_cause', f'Created vacation cause {cause.name}')
        flash(_('Vacation cause created successfully.'), 'success')
        return redirect(url_for('admin.causes'))
    return render_template('admin/cause_form.html', form=form, title=_('New Vacation Cause'))


@bp.route('/causes/<int:cause_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def cause_edit(cause_id):
    cause = db.session.get(VacationCause, cause_id)
    if not cause:
        flash(_('Cause not found.'), 'danger')
        return redirect(url_for('admin.causes'))
    form = VacationCauseForm(obj=cause)
    if form.validate_on_submit():
        cause.name = form.name.data
        cause.name_el = form.name_el.data or None
        cause.is_active = form.is_active.data
        db.session.commit()
        log_audit('edit_cause', f'Edited vacation cause {cause.name}')
        flash(_('Vacation cause updated successfully.'), 'success')
        return redirect(url_for('admin.causes'))
    return render_template('admin/cause_form.html', form=form, cause=cause, title=_('Edit Vacation Cause'))


@bp.route('/causes/<int:cause_id>/delete', methods=['POST'])
@login_required
@admin_required
def cause_delete(cause_id):
    cause = db.session.get(VacationCause, cause_id)
    if not cause:
        flash(_('Cause not found.'), 'danger')
        return redirect(url_for('admin.causes'))
    db.session.delete(cause)
    db.session.commit()
    log_audit('delete_cause', f'Deleted vacation cause {cause.name}')
    flash(_('Vacation cause deleted successfully.'), 'success')
    return redirect(url_for('admin.causes'))


@bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
@admin_required
def department_delete(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept:
        flash(_('Department not found.'), 'danger')
        return redirect(url_for('admin.departments'))
    members = User.query.filter_by(department_id=dept_id).count()
    if members > 0:
        flash(_('Cannot delete department with active members.'), 'danger')
        return redirect(url_for('admin.departments'))
    db.session.delete(dept)
    db.session.commit()
    log_audit('delete_department', f'Deleted department {dept.name}')
    flash(_('Department deleted successfully.'), 'success')
    return redirect(url_for('admin.departments'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(_('User not found.'), 'danger')
        return redirect(url_for('admin.users'))
    if user.id == current_user.id:
        flash(_('You cannot delete yourself.'), 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    log_audit('delete_user', f'Deleted user {user.username}')
    flash(_('User deleted successfully.'), 'success')
    return redirect(url_for('admin.users'))


@bp.route('/holidays')
@login_required
@admin_required
def holidays():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = GreekHoliday.query
    if q:
        query = query.filter(GreekHoliday.name.ilike(f'%{q}%'))
    all_holidays = query.order_by(GreekHoliday.date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/holidays.html', holidays=all_holidays)


@bp.route('/holidays/new', methods=['GET', 'POST'])
@login_required
@admin_required
def holiday_new():
    form = HolidayForm()
    if form.validate_on_submit():
        if GreekHoliday.query.filter_by(date=form.date.data).first():
            flash(_('A holiday on this date already exists.'), 'danger')
            return render_template('admin/holiday_form.html', form=form, title=_('New Holiday'))
        holiday = GreekHoliday(
            date=form.date.data,
            name=form.name.data,
            name_el=form.name_el.data or None,
        )
        db.session.add(holiday)
        db.session.commit()
        log_audit('create_holiday', f'Created holiday {holiday.name} on {holiday.date}')
        flash(_('Holiday added successfully.'), 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', form=form, title=_('New Holiday'))


@bp.route('/holidays/import', methods=['GET', 'POST'])
@login_required
@admin_required
def holiday_import():
    form = HolidayImportForm()
    if form.validate_on_submit():
        f = form.csv_file.data
        stream = f.stream.read().decode('utf-8-sig').splitlines()
        reader = csv.reader(stream)
        next(reader, None)
        imported = 0
        skipped = 0
        for line in reader:
            if not line or not line[0].strip():
                continue
            try:
                date = datetime.strptime(line[0].strip(), '%d/%m/%Y').date()
            except (ValueError, IndexError):
                skipped += 1
                continue
            if GreekHoliday.query.filter_by(date=date).first():
                skipped += 1
                continue
            name = line[1].strip() if len(line) > 1 else ''
            name_el = line[2].strip() if len(line) > 2 else ''
            holiday = GreekHoliday(date=date, name=name, name_el=name_el or None)
            db.session.add(holiday)
            imported += 1
        db.session.commit()
        log_audit('import_holidays', f'Imported {imported} holidays, skipped {skipped}')
        flash(_('Imported %(imported)s holidays, %(skipped)s skipped.', imported=imported, skipped=skipped), 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_import.html', form=form)


@bp.route('/holidays/<int:holiday_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def holiday_edit(holiday_id):
    holiday = db.session.get(GreekHoliday, holiday_id)
    if not holiday:
        flash(_('Holiday not found.'), 'danger')
        return redirect(url_for('admin.holidays'))
    form = HolidayForm(obj=holiday)
    if form.validate_on_submit():
        existing = GreekHoliday.query.filter_by(date=form.date.data).first()
        if existing and existing.id != holiday.id:
            flash(_('A holiday on this date already exists.'), 'danger')
            return render_template('admin/holiday_form.html', form=form, holiday=holiday, title=_('Edit Holiday'))
        holiday.date = form.date.data
        holiday.name = form.name.data
        holiday.name_el = form.name_el.data or None
        db.session.commit()
        log_audit('edit_holiday', f'Edited holiday {holiday.name}')
        flash(_('Holiday updated successfully.'), 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', form=form, holiday=holiday, title=_('Edit Holiday'))


@bp.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
@login_required
@admin_required
def holiday_delete(holiday_id):
    holiday = db.session.get(GreekHoliday, holiday_id)
    if not holiday:
        flash(_('Holiday not found.'), 'danger')
        return redirect(url_for('admin.holidays'))
    db.session.delete(holiday)
    db.session.commit()
    log_audit('delete_holiday', f'Deleted holiday {holiday.name}')
    flash(_('Holiday deleted successfully.'), 'success')
    return redirect(url_for('admin.holidays'))


@bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = AuditLog.query
    if q:
        query = query.filter(
            db.or_(
                AuditLog.action.ilike(f'%{q}%'),
                AuditLog.username.ilike(f'%{q}%'),
                AuditLog.details.ilike(f'%{q}%'),
            )
        )
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit_log.html', logs=logs)


@bp.route('/logs', methods=['GET', 'POST'])
@login_required
@admin_required
def logs():
    log_file = os.path.join(current_app.config.get('LOG_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')), 'app.jsonl')
    entries = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    level_filter = request.args.get('level', '').strip()
    q = request.args.get('q', '').strip()
    if level_filter:
        entries = [e for e in entries if e.get('level') == level_filter]
    if q:
        ql = q.lower()
        entries = [e for e in entries if ql in e.get('message', '').lower() or ql in e.get('module', '').lower() or ql in e.get('logger', '').lower()]
    entries.reverse()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    if per_page not in (20, 50, 100, 200):
        per_page = 50
    total = len(entries)
    offset = (page - 1) * per_page
    page_entries = entries[offset:offset + per_page]
    log_audit('view_logs', f'Viewed application logs (level={level_filter or "ALL"}, q={q or ""})')
    return render_template('admin/logs.html', entries=page_entries, page=page, per_page=per_page, total=total, level_filter=level_filter, q=q)
