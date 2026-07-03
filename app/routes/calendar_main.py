from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.vacation import VacationRequest
from app.models.holiday import GreekHoliday

bp = Blueprint('calendar_main', __name__, url_prefix='/api')


@bp.route('/calendar/events')
@login_required
def calendar_events():
    start_str = request.args.get('start', '')
    end_str = request.args.get('end', '')

    from datetime import datetime
    try:
        start = datetime.strptime(start_str[:10], '%Y-%m-%d').date() if start_str else None
        end = datetime.strptime(end_str[:10], '%Y-%m-%d').date() if end_str else None
    except (ValueError, TypeError):
        start = end = None

    if current_user.is_hr or current_user.is_admin:
        query = VacationRequest.query
    elif current_user.is_manager:
        sub_ids = [u.id for u in User.query.filter_by(manager_id=current_user.id).all()]
        sub_ids.append(current_user.id)
        query = VacationRequest.query.filter(VacationRequest.user_id.in_(sub_ids))
    else:
        query = VacationRequest.query.filter(
            db.or_(
                VacationRequest.user_id == current_user.id,
                VacationRequest.user_id.in_(
                    db.session.query(User.id).filter(User.department_id == current_user.department_id)
                )
            )
        )

    query = query.filter(VacationRequest.status.in_(['approved', 'pending', 'hr_assigned']))

    if start:
        query = query.filter(VacationRequest.end_date >= start)
    if end:
        query = query.filter(VacationRequest.start_date <= end)

    vacations = query.all()

    events = []
    status_colors = {
        'approved': '#28a745',
        'pending': '#ffc107',
        'hr_assigned': '#17a2b8',
    }

    for vac in vacations:
        title = f'{vac.user.display_name or vac.user.username}'
        if vac.request_type == 'hr_assigned' and vac.cause:
            title += f' ({vac.cause.name})'
        events.append({
            'id': vac.id,
            'title': title,
            'start': vac.start_date.isoformat(),
            'end': vac.end_date.isoformat(),
            'color': status_colors.get(vac.status, '#6c757d'),
            'textColor': '#fff' if vac.status in ['approved', 'hr_assigned'] else '#000',
            'extendedProps': {
                'status': vac.status,
                'type': vac.request_type,
                'days': vac.days_count,
                'username': vac.user.display_name or vac.user.username,
                'department': vac.user.department.name if vac.user.department else '',
            }
        })

    holidays = GreekHoliday.query.all()
    user_locale = getattr(current_user, 'locale', None) or 'en'
    for h in holidays:
        # Use Greek name when user locale is 'el' and a Greek name exists
        title = h.name_el if (user_locale.startswith('el') and h.name_el) else h.name
        events.append({
            'id': f'holiday-{h.id}',
            'title': title,
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

    return jsonify(events)
