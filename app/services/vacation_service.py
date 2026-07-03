from datetime import date, timedelta
from app.extensions import db
from app.models.holiday import GreekHoliday


def get_greek_holidays(year=None):
    if year is None:
        year = date.today().year
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return GreekHoliday.query.filter(
        GreekHoliday.date >= start,
        GreekHoliday.date <= end
    ).all()


def is_weekend(d):
    return d.weekday() >= 5


def is_holiday(d):
    return GreekHoliday.query.filter_by(date=d).first() is not None


def is_working_day(d):
    return not is_weekend(d) and not is_holiday(d)


def count_working_days(start_date, end_date):
    days = 0
    current = start_date
    while current <= end_date:
        if is_working_day(current):
            days += 1
        current += timedelta(days=1)
    return days


def get_working_days_in_range(start_date, end_date):
    result = []
    current = start_date
    while current <= end_date:
        if is_working_day(current):
            result.append(current)
        current += timedelta(days=1)
    return result
