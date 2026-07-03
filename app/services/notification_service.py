import smtplib
from email.message import EmailMessage
from flask import current_app, render_template, url_for
from flask_babel import gettext as _, force_locale
from app.extensions import db
from app.models.notification import Notification
from app.models.setting import EmailSetting


def _get_email_locale():
    return EmailSetting.get('EMAIL_LOCALE', 'en')


def send_notification(user_id, title, message, type='info', link=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False,
        type=type,
        link=link,
    )
    db.session.add(notification)
    db.session.commit()


def _get_email_config():
    return {
        'server': EmailSetting.get('SMTP_SERVER'),
        'port': int(EmailSetting.get('SMTP_PORT', '587')),
        'user': EmailSetting.get('SMTP_USER', ''),
        'password': EmailSetting.get('SMTP_PASSWORD', ''),
        'from_addr': EmailSetting.get('SMTP_FROM', ''),
        'use_tls': EmailSetting.get('SMTP_USE_TLS', '1') == '1',
        'no_auth': EmailSetting.get('SMTP_NO_AUTH', '0') == '1',
        'text_only': EmailSetting.get('SMTP_TEXT_ONLY', '0') == '1',
    }


def send_email_notification(recipient_email, subject, body_html, body_text=None):
    cfg = _get_email_config()
    if not cfg['server'] or not cfg['port'] or not cfg['from_addr']:
        return

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = cfg['from_addr']
        msg['To'] = recipient_email

        if cfg['text_only']:
            msg.set_content(body_text or body_html)
        else:
            msg.set_content(body_text or body_html)
            msg.add_alternative(body_html, subtype='html')

        with smtplib.SMTP(cfg['server'], cfg['port'], timeout=10) as server:
            if cfg['use_tls']:
                server.starttls()
            if not cfg['no_auth'] and cfg['user']:
                server.login(cfg['user'], cfg['password'])
            server.send_message(msg)
    except Exception as e:
        current_app.logger.error(f'Email send failed to {recipient_email}: {e}')


def _fmt_dates(request_obj):
    return (request_obj.start_date.strftime('%d/%m/%Y'),
            request_obj.end_date.strftime('%d/%m/%Y'))


def _with_locale(func, *args, **kwargs):
    locale = _get_email_locale()
    with force_locale(locale):
        return func(*args, **kwargs)


def notify_vacation_created(request_obj):
    user = request_obj.user
    manager = user.manager
    start_fmt, end_fmt = _fmt_dates(request_obj)
    title = _('New Vacation Request')
    message = _('%(name)s submitted a vacation request from %(start)s to %(end)s.',
                name=user.display_name or user.username,
                start=start_fmt, end=end_fmt)

    if manager:
        send_notification(manager.id, title, message, 'info',
                          link=f'/manager/approve/{request_obj.id}')
        if manager.email:
            def _send():
                body_html = render_template('emails/new_request.html', request=request_obj, user=user, recipient=manager)
                body_text = _('%(name)s submitted a vacation request from %(start)s to %(end)s.\n\n'
                              'This request requires your approval.\n'
                              'Please log in to approve or reject it.\n\n'
                              'Review at: %(url)s',
                              name=user.display_name or user.username,
                              start=start_fmt, end=end_fmt,
                              url=url_for('manager.approve_request', req_id=request_obj.id, _external=True))
                send_email_notification(manager.email, title, body_html, body_text)
            _with_locale(_send)


def notify_vacation_approved(request_obj, approved_by):
    start_fmt, end_fmt = _fmt_dates(request_obj)
    title = _('Vacation Approved')
    message = _('Your vacation request from %(start)s to %(end)s has been approved.',
                start=start_fmt, end=end_fmt)
    send_notification(request_obj.user_id, title, message, 'success', link='/vacation/my-vacations')

    user = request_obj.user
    if user.email:
        def _send():
            body_html = render_template('emails/approved.html', request=request_obj, approved_by=approved_by, user=user)
            body_text = _('Your vacation from %(start)s to %(end)s has been approved.',
                          start=start_fmt, end=end_fmt)
            send_email_notification(user.email, title, body_html, body_text)
        _with_locale(_send)


def notify_vacation_rejected(request_obj, approved_by, comment=None):
    start_fmt, end_fmt = _fmt_dates(request_obj)
    title = _('Vacation Rejected')
    message = _('Your vacation request from %(start)s to %(end)s has been rejected.',
                start=start_fmt, end=end_fmt)
    send_notification(request_obj.user_id, title, message, 'danger', link='/vacation/my-vacations')

    user = request_obj.user
    if user.email:
        def _send():
            body_html = render_template('emails/rejected.html', request=request_obj, approved_by=approved_by, comment=comment, user=user)
            body_text = _('Your vacation from %(start)s to %(end)s has been rejected.', start=start_fmt, end=end_fmt)
            if comment:
                body_text += f'\n{_("Comment")}: {comment}'
            send_email_notification(user.email, title, body_html, body_text)
        _with_locale(_send)


def notify_vacation_cancelled(request_obj):
    user = request_obj.user
    manager = user.manager
    start_fmt, end_fmt = _fmt_dates(request_obj)
    title = _('Vacation Cancelled')
    message = _('%(name)s cancelled their vacation request from %(start)s to %(end)s.',
                name=user.display_name or user.username,
                start=start_fmt, end=end_fmt)

    if manager:
        send_notification(manager.id, title, message, 'warning')
        if manager.email:
            def _send():
                send_email_notification(manager.email, title, message, message)
            _with_locale(_send)


def notify_hr_assigned(request_obj, assigned_by):
    start_fmt, end_fmt = _fmt_dates(request_obj)
    title = _('Vacation Assigned')
    message = _('A vacation from %(start)s to %(end)s has been assigned to you.',
                start=start_fmt, end=end_fmt)
    send_notification(request_obj.user_id, title, message, 'success', link='/vacation/my-vacations')

    user = request_obj.user
    if user.email:
        def _send():
            body_html = render_template('emails/assigned.html', request=request_obj, assigned_by=assigned_by, user=user)
            body_text = _('A vacation from %(start)s to %(end)s has been assigned to you.',
                          start=start_fmt, end=end_fmt)
            send_email_notification(user.email, title, body_html, body_text)
        _with_locale(_send)
