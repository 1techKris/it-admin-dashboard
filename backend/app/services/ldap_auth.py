from ldap3 import Server, Connection, ALL
from app.core.config import settings

def authenticate_ldap_user(username: str, password: str):
    server = Server(settings.LDAP_SERVER, get_info=ALL)

    user_dn = f"{username}@yourdomain.local"

    # Attempt bind as user
    conn = Connection(server, user=user_dn, password=password, auto_bind=True)

    # Search user record
    conn.search(
        search_base=settings.LDAP_BASE_DN,
        search_filter=settings.LDAP_USER_FILTER.format(username=username),
        attributes=["memberOf", "displayName", "mail"]
    )

    if not conn.entries:
        raise ValueError("User not found")

    entry = conn.entries[0]

    return {
        "username": username,
        "display_name": entry.displayName.value,
        "email": entry.mail.value,
        "groups": entry.memberOf.values if "memberOf" in entry else [],
    }