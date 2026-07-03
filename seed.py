#!/usr/bin/env python3
"""Seed script to create initial admin user and sample data."""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.models.vacation import VacationCause

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            email='admin@company.com',
            display_name='Administrator',
            is_admin=True,
            is_hr=True,
            is_active=True,
            vacation_days_per_year=0,
        )
        admin.set_password('admin123')
        db.session.add(admin)

    if not User.query.filter_by(username='manager').first():
        mgr = User(
            username='manager',
            email='manager@company.com',
            display_name='Department Manager',
            is_active=True,
            vacation_days_per_year=22,
        )
        mgr.set_password('manager123')
        db.session.add(mgr)

    if not User.query.filter_by(username='hr_user').first():
        hr_user = User(
            username='hr_user',
            email='hr@company.com',
            display_name='HR Manager',
            is_hr=True,
            is_active=True,
            vacation_days_per_year=22,
        )
        hr_user.set_password('hr123')
        db.session.add(hr_user)

    if not User.query.filter_by(username='employee').first():
        emp = User(
            username='employee',
            email='employee@company.com',
            display_name='John Employee',
            is_active=True,
            vacation_days_per_year=20,
        )
        emp.set_password('emp123')
        db.session.add(emp)

    db.session.commit()

    if not Department.query.first():
        dept_it = Department(name='IT', name_el='Πληροφορική')
        dept_hr = Department(name='Human Resources', name_el='Ανθρώπινο Δυναμικό')
        dept_finance = Department(name='Finance', name_el='Οικονομικό')
        dept_ops = Department(name='Operations', name_el='Λειτουργίες')
        db.session.add_all([dept_it, dept_hr, dept_finance, dept_ops])
        db.session.commit()

    if not VacationCause.query.first():
        causes = [
            VacationCause(name='Annual Leave', name_el='Κανονική Άδεια', is_active=True),
            VacationCause(name='Medical Leave', name_el='Αναρρωτική Άδεια', is_active=True),
            VacationCause(name='Parental Leave', name_el='Γονική Άδεια', is_active=True),
            VacationCause(name='Personal Leave', name_el='Προσωπική Άδεια', is_active=True),
            VacationCause(name='Emergency Leave', name_el='Άδεια Εκτάκτου Ανάγκης', is_active=True),
            VacationCause(name='Caregiver Leave', name_el='Άδεια Φροντίδας', is_active=True),
            VacationCause(name='Summer Leave', name_el='Θερινή Άδεια', is_active=True),
            VacationCause(name='Christmas Leave', name_el='Άδεια Χριστουγέννων', is_active=True),
            VacationCause(name='Easter Leave', name_el='Άδεια Πάσχα', is_active=True),
            VacationCause(name='Remote Work', name_el='Τηλεργασία', is_active=True),
            VacationCause(name='Company Shutdown', name_el='Αργία Εταιρείας', is_active=True),
            VacationCause(name='Mandatory Leave', name_el='Υποχρεωτική Άδεια', is_active=True),
            VacationCause(name='Training / Seminar', name_el='Εκπαίδευση / Σεμινάριο', is_active=True),
        ]
        db.session.add_all(causes)
        db.session.commit()

    print('Database seeded successfully!')
    print('Admin user: admin / admin123')
    print('Manager user: manager / manager123')
    print('HR user: hr_user / hr123')
    print('Employee user: employee / emp123')
