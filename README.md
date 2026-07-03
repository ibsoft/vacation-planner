# Vacation Planner

A web-based vacation/leave management application with Active Directory integration, role-based approval workflows, internationalization (English/Greek), email notifications, and team calendaring.

Built with **Flask**, **SQLAlchemy**, **FullCalendar**, and **Flask-Babel**.

---

## Features

- **Active Directory / LDAP Authentication & User Import**
  Authenticate users against AD/LDAP. Import users from AD with preview and selective import. Supports NTLM, configurable attributes (sAMAccountName, mail, department, manager, displayName).

- **Role-Based Access Control**
  - **User** — submit, cancel, and view own vacation requests; request date changes
  - **Manager** — approve/reject team requests; respond to change requests; export team vacation plans to Excel
  - **HR** — manage all users' vacation days, assign vacation to any user, view all requests
  - **Admin** — full system configuration: users, departments, vacation causes, Greek holidays, LDAP/email settings, audit log, application logs
  - **Top Management** — elevated visibility across departments without admin/HR privileges

- **Vacation Request & Approval Workflow**
  Users submit requests with date range, vacation cause, and optional custom reason. Requests go to the user's manager for approval. HR can also assign vacation directly.

- **Change Request Workflow**
  Users can request date changes to approved or pending vacations. Managers approve or reject the change; accepted changes auto-update dates and days count.

- **Team Calendar with FullCalendar**
  Interactive calendar using FullCalendar. Shows all team vacations (color-coded by status: approved/pending/HR-assigned) and Greek holidays as background events. Supports department filtering.

- **In-App Notifications**
  Bell-icon notification dropdown in the navbar. Unread badge count. Notifications for created, approved, rejected, cancelled, assigned, and changed requests. Each notification links to the relevant page.

- **Email Notifications (SMTP)**
  Sends HTML (or plain-text) emails for vacation created, approved, rejected, cancelled, and HR-assigned events. Configurable via admin UI. Supports TLS and **no-authentication (anonymous SMTP)**.

- **i18n — English & Greek**
  Fully translated UI (English / Ελληνικά) using Flask-Babel. Translations stored in `app/translations/`. `gettext` used throughout Python, Jinja2 templates, and WTForms (lazy_gettext). Users can switch language in-profile or via `?lang=en|el`. Email locale independently configurable.

- **Fancy Excel Exports**
  Exports approved vacation plans to `.xlsx` via openpyxl with styled headers, alternating row colors, **SUM and AVERAGE formulas** on the days column, auto-filter, and frozen panes.

- **Vacation Causes**
  Configurable vacation cause types (e.g. Annual Leave, Medical Leave, Remote Work, Training). Bilingual names (EN/EL). Causes can be toggled active/inactive.

- **Greek Holidays**
  Manage Greek national/religious holidays with bilingual names. Holidays are marked as background events on the calendar and excluded from working-day calculations. **CSV import** support for bulk holiday loading.

- **Audit Logging**
  All significant actions (user creation, login/logout, approvals, AD imports, settings changes, etc.) are recorded with timestamp, user, IP address, and details. Viewable in the admin panel.

- **JSON Application Logging with Rotation**
  Application logs written as rotating JSON lines (`logs/app.jsonl`, 10 MB per file, 5 backups). Viewable in the admin panel with filtering by level and search.

- **User Profiles & Avatars**
  Users can edit their profile (display name, email, phone, mobile, internal phone, language). Gravatar support (automatic from email). Manual avatar upload (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`).

- **Vacation Date Editing (Change Request)**
  Users submit a change request with new dates and a reason. The change goes through the same manager approval pipeline. On approval, the vacation record is updated.

---

## Quick Start (Development with SQLite)

```bash
git clone <repository-url>
cd vacation-planner

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

flask db upgrade
flask seed-data

flask run
```

The app will be available at `http://localhost:5000`.

### Default Accounts (from seed)

| Username    | Password    | Role    |
|-------------|-------------|---------|
| admin       | admin123    | Admin   |
| manager     | manager123  | Manager |
| hr_user     | hr123       | HR      |
| employee    | emp123      | User    |

---

## Production Setup (PostgreSQL)

### 1. Install PostgreSQL

```bash
sudo apt install postgresql postgresql-client libpq-dev   # Debian/Ubuntu
sudo -u postgres createdb vacation_planner
sudo -u postgres createuser vacation_user -P
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vacation_planner TO vacation_user;"
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
pip install psycopg2-binary
```

### 3. Set environment variables

```bash
export DATABASE_URL=postgresql://vacation_user:your-password@localhost/vacation_planner
export SECRET_KEY=your-very-secure-secret-key
```

### 4. Run migrations & seed

```bash
flask db upgrade
flask seed-data
```

### 5. Run with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 'app:create_app()' --bind 0.0.0.0:8000
```

### 6. systemd service (optional)

Create `/etc/systemd/system/vacation-planner.service`:

```ini
[Unit]
Description=Vacation Planner
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/vacation-planner
Environment="DATABASE_URL=postgresql://user:pass@localhost/vacation_planner"
Environment="SECRET_KEY=your-secret-key"
ExecStart=/opt/vacation-planner/venv/bin/gunicorn -w 4 'app:create_app()' --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 7. Docker (via Gunicorn)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary gunicorn
COPY . .
CMD ["gunicorn", "-w", "4", "'app:create_app()'", "--bind", "0.0.0.0:8000"]
```

---

## Configuration Reference

All configuration is via environment variables. Secrets should never be committed.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///instance/vacations.db` | Database connection URI (SQLite for dev, PostgreSQL for production) |
| `SECRET_KEY` | `change-this-secret-key-in-production` | Flask secret key for sessions and CSRF |
| `LDAP_SERVER` | `ldap://localhost:389` | LDAP server URL (overridable via admin UI) |
| `LDAP_BASE_DN` | `dc=example,dc=com` | LDAP base DN |
| `LDAP_BIND_DN` | `cn=admin,dc=example,dc=com` | LDAP bind DN |
| `LDAP_BIND_PASSWORD` | `` | LDAP bind password |
| `LDAP_USER_FILTER` | `(objectClass=user)` | LDAP search filter |
| `LDAP_USERNAME_ATTR` | `sAMAccountName` | LDAP attribute for username |
| `LDAP_EMAIL_ATTR` | `mail` | LDAP attribute for email |
| `LDAP_DEPT_ATTR` | `department` | LDAP attribute for department |
| `LDAP_MANAGER_ATTR` | `manager` | LDAP attribute for manager DN |
| `LDAP_DISPLAY_NAME_ATTR` | `displayName` | LDAP attribute for display name |

> **Note:** LDAP and Email settings can also be managed at runtime through the admin UI. Values entered there persist in the database and override environment variables.

---

## AD / LDAP Setup

1. Navigate to **Admin → AD Settings**.
2. Configure:
   - **LDAP Server** — e.g. `ldap://dc01.company.local:389`
   - **Base DN** — e.g. `dc=company,dc=local`
   - **Bind DN** — service account DN
   - **Bind Password**
   - **User Filter** — e.g. `(&(objectClass=user)(objectCategory=person))`
   - **Attribute mappings** — defaults work for Active Directory
3. Click **Test Connection** to verify.
4. Go to **Admin → Import from AD** to browse and import users with preview.

Users imported from AD are created in the local database. Subsequent imports update existing users (email, display name, AD GUID, DN).

---

## Email Setup

1. Navigate to **Admin → Email Settings**.
2. Configure:
   - **SMTP Server** — e.g. `smtp.company.com`
   - **SMTP Port** — `587` (STARTTLS), `465` (SSL), or `25` (plain)
   - **SMTP Username / Password** — or enable **No Authentication** for anonymous relays
   - **From Email** — sender address
   - **Use TLS** — enables STARTTLS
   - **Text Only** — send plain text instead of HTML
   - **Email Language** — independent from user locale
3. Click **Send Test Email** to verify.

The `SMTP_NO_AUTH` option allows connecting to mail relays that do not require login (useful with local sendmail/Postfix or services like SendGrid's SMTP relay).

---

## Internationalization (i18n)

The app supports **English** and **Greek (Ελληνικά)**.

### Adding new translatable strings

1. Wrap strings in `gettext()` / `_()` (Python) or `{% trans %}` / `_()` (Jinja2).
2. Extract new strings:

```bash
pybabel extract -F babel.cfg -o messages.pot .
```

3. Update `.po` files:

```bash
pybabel update -i messages.pot -d app/translations
```

4. Edit the `.po` files in `app/translations/<lang>/LC_MESSAGES/messages.po`.
5. Compile:

```bash
pybabel compile -d app/translations
```

### Adding a new language

```bash
pybabel init -i messages.pot -d app/translations -l fr
```

Then add `'fr': 'Français'` to the `LANGUAGES` dict in `config.py` and wire it in `get_locale()` in `app/__init__.py`.

---

## Project Structure

```
vacation-planner/
├── app/
│   ├── __init__.py          # Application factory, logging, i18n init
│   ├── extensions.py        # Flask extensions (db, migrate, login, babel)
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── admin_forms.py   # User, Department, LDAP, Email, Holiday, Cause forms
│   │   ├── auth_forms.py    # Login, Profile forms
│   │   ├── hr_forms.py      # Set days, Assign vacation forms
│   │   ├── manager_forms.py # Approval form
│   │   └── vacation_forms.py# Request, Change request forms
│   ├── models/
│   │   ├── __init__.py
│   │   ├── audit.py         # AuditLog
│   │   ├── department.py    # Department
│   │   ├── holiday.py       # GreekHoliday
│   │   ├── notification.py  # In-app notifications
│   │   ├── setting.py       # LdapSetting, EmailSetting (key-value store)
│   │   ├── user.py          # User (AD support, roles, gravatar)
│   │   └── vacation.py      # VacationRequest, VacationCause, VacationAssignment
│   ├── routes/
│   │   ├── __init__.py      # Decorators: admin_required, hr_required, log_audit
│   │   ├── admin.py         # Admin dashboard, users, departments, causes, holidays, LDAP, email, audit, logs
│   │   ├── auth.py          # Login, logout, profile, language switcher
│   │   ├── calendar_main.py # FullCalendar JSON API endpoint
│   │   ├── hr.py            # HR dashboard, set days, assign vacation, all vacations
│   │   ├── manager.py       # Manager dashboard, approve/reject, change responses, Excel export
│   │   ├── notifications.py # Mark notification as read
│   │   └── vacation.py      # User dashboard, new request, my vacations, cancel, change request, team calendar
│   ├── services/
│   │   ├── __init__.py
│   │   ├── export_service.py    # Excel export with formulas
│   │   ├── ldap_service.py      # LDAP authentication & user search
│   │   ├── notification_service.py # In-app & email notifications
│   │   └── vacation_service.py  # Working-day counting, holiday detection
│   ├── static/               # CSS, JS, uploaded avatars
│   ├── templates/
│   │   ├── admin/            # Admin panel templates
│   │   ├── auth/             # Login, profile
│   │   ├── emails/           # Email templates (HTML)
│   │   ├── hr/               # HR dashboard, assign, users
│   │   ├── macros/           # Pagination macro
│   │   ├── manager/          # Manager dashboard, approve, team
│   │   ├── vacation/         # User dashboard, new request, calendar, change
│   │   └── base.html         # Main layout navbar, notifications
│   └── translations/
│       ├── el/LC_MESSAGES/messages.{po,mo}
│       └── en/LC_MESSAGES/messages.{po,mo}
├── config.py                 # App configuration (Flask + LDAP env vars)
├── manage.py                 # Flask CLI entry point
├── run.py                    # Development server entry point
├── seed.py                   # Database seeding script (flask seed-data)
├── babel.cfg                 # Babel extraction config
├── requirements.txt          # Python dependencies
├── migrations/               # Alembic / Flask-Migrate
├── logs/                     # Rotating JSON logs (app.jsonl)
├── instance/                 # SQLite DB & Flask session files (gitignored)
├── .env                      # Environment variables (gitignored)
└── README.md
```

---

## License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0). See the [LICENSE](LICENSE) file for details.
