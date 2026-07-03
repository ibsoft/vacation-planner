import ldap3
from ldap3 import Server, Connection, ALL, NTLM
from flask import current_app


def get_ldap_connection():
    server = Server(current_app.config['LDAP_SERVER'], get_info=ALL)
    return Connection(
        server,
        user=current_app.config['LDAP_BIND_DN'],
        password=current_app.config['LDAP_BIND_PASSWORD'],
        auto_bind=True
    )


def authenticate(username, password):
    try:
        server = Server(current_app.config['LDAP_SERVER'], get_info=ALL)
        user_dn = find_user_dn(username)
        if not user_dn:
            return None
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        return user_dn
    except Exception:
        return None


def find_user_dn(username):
    try:
        conn = get_ldap_connection()
        base_dn = current_app.config['LDAP_BASE_DN']
        username_attr = current_app.config['LDAP_USERNAME_ATTR']
        user_filter = current_app.config['LDAP_USER_FILTER']
        search_filter = f'(&{user_filter}({username_attr}={username}))'
        conn.search(base_dn, search_filter, attributes=['*'])
        if len(conn.entries) > 0:
            return conn.entries[0].entry_dn
        return None
    except Exception:
        return None


def search_users(search_base=None):
    try:
        conn = get_ldap_connection()
        base_dn = search_base or current_app.config['LDAP_BASE_DN']
        user_filter = current_app.config['LDAP_USER_FILTER']
        attrs = [
            current_app.config['LDAP_USERNAME_ATTR'],
            current_app.config['LDAP_EMAIL_ATTR'],
            current_app.config['LDAP_DEPT_ATTR'],
            current_app.config['LDAP_MANAGER_ATTR'],
            current_app.config['LDAP_DISPLAY_NAME_ATTR'],
            'objectGUID',
        ]
        conn.search(base_dn, user_filter, attributes=attrs)
        users = []
        for entry in conn.entries:
            username_attr = current_app.config['LDAP_USERNAME_ATTR']
            user_data = {
                'dn': entry.entry_dn,
                'username': str(getattr(entry, username_attr, '')),
                'email': str(getattr(entry, current_app.config['LDAP_EMAIL_ATTR'], '')),
                'department': str(getattr(entry, current_app.config['LDAP_DEPT_ATTR'], '')),
                'manager_dn': str(getattr(entry, current_app.config['LDAP_MANAGER_ATTR'], '')),
                'display_name': str(getattr(entry, current_app.config['LDAP_DISPLAY_NAME_ATTR'], '')),
            }
            guid = getattr(entry, 'objectGUID', None)
            if guid is not None:
                if isinstance(guid, list) and len(guid) > 0:
                    guid = guid[0]
                if isinstance(guid, bytes):
                    user_data['guid'] = '-'.join(
                        [guid[0:4].hex(), guid[4:6].hex(), guid[6:8].hex(),
                         guid[8:10].hex(), guid[10:16].hex()]
                    ).upper()
                elif isinstance(guid, str):
                    user_data['guid'] = guid.upper()
                else:
                    user_data['guid'] = str(guid)
            else:
                user_data['guid'] = ''
            users.append(user_data)
        return users
    except Exception as e:
        current_app.logger.error(f'LDAP search error: {e}')
        return []


def get_user_attributes(dn):
    try:
        conn = get_ldap_connection()
        conn.search(dn, '(objectClass=*)', attributes=['*'], search_scope='BASE')
        if len(conn.entries) > 0:
            return conn.entries[0]
        return None
    except Exception:
        return None
