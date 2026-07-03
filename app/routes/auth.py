from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.forms.auth_forms import LoginForm, ProfileForm
from app.services.ldap_service import authenticate, get_user_attributes
from app.routes import log_audit
import os

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('vacation.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        ldap_dn = None
        authenticated = False

        if user and user.ad_dn:
            try:
                ldap_dn = authenticate(username, password)
                if ldap_dn:
                    authenticated = True
            except Exception:
                pass

        if not authenticated and user and user.password_hash:
            authenticated = user.check_password(password)

        if authenticated and user and user.is_active:
            login_user(user, remember=True)
            session['lang'] = user.locale or 'en'
            log_audit('login', f'User {username} logged in')
            next_page = request.args.get('next')
            flash(_('Welcome back, %(name)s!', name=user.display_name or user.username), 'success')
            if user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            elif user.is_hr:
                return redirect(next_page or url_for('hr.dashboard'))
            return redirect(next_page or url_for('vacation.dashboard'))
        elif user and not user.is_active:
            flash(_('Your account is disabled. Contact your administrator.'), 'danger')
        else:
            flash(_('Invalid username or password.'), 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    log_audit('logout', f'User {current_user.username} logged out')
    session.clear()
    logout_user()
    flash(_('You have been logged out.'), 'info')
    return redirect(url_for('auth.login'))


@bp.route('/lang/<locale>')
def set_lang(locale):
    if locale in ['en', 'el']:
        session['lang'] = locale
        if current_user.is_authenticated:
            current_user.locale = locale
            db.session.commit()
    referrer = request.referrer or url_for('vacation.dashboard' if current_user.is_authenticated else 'auth.login')
    return redirect(referrer)


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data or None
        current_user.email = form.email.data or None
        current_user.phone = form.phone.data or None
        current_user.mobile = form.mobile.data or None
        current_user.internal_phone = form.internal_phone.data or None
        current_user.locale = form.locale.data
        # email_locale empty string means use system default
        current_user.email_locale = form.email_locale.data or None
        if form.avatar.data:
            allowed_mimes = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
            mime = form.avatar.data.content_type
            if mime not in allowed_mimes:
                flash(_('Invalid file type.'), 'error')
                return redirect(url_for('auth.profile'))
            ext = form.avatar.data.filename.rsplit('.', 1)[-1].lower()
            filename = f'avatar_{current_user.id}_{int(__import__("time").time())}.{ext}'
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
            os.makedirs(upload_dir, exist_ok=True)
            form.avatar.data.save(os.path.join(upload_dir, filename))
            current_user.avatar_url = url_for('static', filename=f'uploads/avatars/{filename}')
        db.session.commit()
        session['lang'] = form.locale.data
        flash(_('Profile updated successfully.'), 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html', form=form)
