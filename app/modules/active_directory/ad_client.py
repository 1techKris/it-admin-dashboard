# app/modules/active_directory/ad_client.py

import logging
import time
from typing import List, Dict, Optional, Tuple

from ldap3 import Server, Connection, NTLM, ALL, SUBTREE, ALL_ATTRIBUTES, MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
from ldap3.utils.conv import escape_filter_chars

from app.core.database import SessionLocal
# Reuse your existing global settings key/value helpers
from app.modules.servers.models import get_setting

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ADConfig:
    """Holds Active Directory connection configuration loaded from GlobalSettings."""
    def __init__(self, db):
        self.domain: str = get_setting(db, "ad_domain") or ""                  # e.g., 1sttech.local
        self.host: str = get_setting(db, "ad_dc_host") or ""                   # e.g., 1tech-dc
        self.ip: Optional[str] = get_setting(db, "ad_dc_ip")                   # optional fallback
        self.base_dn: str = get_setting(db, "ad_base_dn") or ""                # e.g., DC=1sttech,DC=local
        self.username: str = get_setting(db, "ad_username") or ""              # e.g., svc_ad
        self.password: str = get_setting(db, "ad_password") or ""              # secret
        self.default_user_ou: Optional[str] = get_setting(db, "ad_default_user_ou")  # for user creation/moves

    @property
    def fqdn(self) -> Optional[str]:
        if self.host and self.domain:
            return f"{self.host}.{self.domain}"
        return None

    def validate(self) -> Tuple[bool, List[str]]:
        errs = []
        if not self.domain:
            errs.append("ad_domain missing")
        if not self.host and not self.ip:
            errs.append("ad_dc_host or ad_dc_ip must be provided")
        if not self.base_dn:
            errs.append("ad_base_dn missing")
        if not self.username or not self.password:
            errs.append("ad_username/ad_password missing")
        return (len(errs) == 0, errs)


class ADClient:
    """
    Active Directory Client (NTLM) with:
      - Domain-wide scope
      - FQDN → hostname → IP connection fallback
      - Full logging
      - Management operations (reset, unlock, enable/disable, move, group membership)
    """

    def __init__(self, db=None):
        # Allow usage either with provided db or ephemeral session
        self._ephemeral_db = False
        if db is None:
            self._ephemeral_db = True
            self.db = SessionLocal()
        else:
            self.db = db

        self.cfg = ADConfig(self.db)
        ok, errs = self.cfg.validate()
        if not ok:
            logger.error("AD config invalid: %s", ", ".join(errs))
            raise ValueError(f"AD config invalid: {errs}")

        self.conn: Optional[Connection] = None

    def __del__(self):
        try:
            if self.conn:
                self.conn.unbind()
        except Exception:
            pass
        if getattr(self, "_ephemeral_db", False) and hasattr(self, "db"):
            try:
                self.db.close()
            except Exception:
                pass

    # ---------------------------
    # Connection
    # ---------------------------
    def connect(self) -> Connection:
        """
        Try FQDN → hostname → IP (as requested).
        NTLM bind with 'DOMAIN\\username' or UPN 'user@domain'.
        """
        candidates = []
        if self.cfg.fqdn:
            candidates.append(self.cfg.fqdn)
        if self.cfg.host:
            candidates.append(self.cfg.host)
        if self.cfg.ip:
            candidates.append(self.cfg.ip)

        # Build bind username — prefer 'DOMAIN\\username' for NTLM.
        bind_user = self.cfg.username
        if "\\" not in bind_user and "@" not in bind_user and self.cfg.domain:
            bind_user = f"{self.cfg.domain.split('.')[0]}\\{self.cfg.username}"

        last_exc = None
        for host in candidates:
            t0 = time.time()
            try:
                logger.debug("[AD] Trying server host=%s domain=%s base_dn=%s bind_user=%s",
                             host, self.cfg.domain, self.cfg.base_dn, bind_user)

                server = Server(host, get_info=ALL, use_ssl=False)  # Plain LDAP by default (NTLM)
                conn = Connection(
                    server,
                    user=bind_user,
                    password=self.cfg.password,
                    authentication=NTLM,
                    auto_bind=True,
                    receive_timeout=10,
                )
                elapsed = (time.time() - t0) * 1000
                logger.info("[AD] Connected to %s (%.1f ms)", host, elapsed)
                self.conn = conn
                return conn
            except Exception as e:
                elapsed = (time.time() - t0) * 1000
                logger.warning("[AD] Connect failed host=%s (%.1f ms) err=%s", host, elapsed, e)
                last_exc = e

        raise RuntimeError(f"[AD] Unable to connect to any server. Last error: {last_exc}")

    def _ensure_conn(self):
        if not self.conn:
            return self.connect()
        if not self.conn.bound:
            return self.connect()
        return self.conn

    # ---------------------------
    # Helpers
    # ---------------------------
    def _search(self, search_base: Optional[str], search_filter: str, attributes=ALL_ATTRIBUTES, size_limit: int = 200):
        conn = self._ensure_conn()
        base = search_base or self.cfg.base_dn
        logger.debug("[AD] Search base=%s filter=%s attrs=%s size=%d",
                     base, search_filter, attributes, size_limit)

        t0 = time.time()
        ok = conn.search(
            search_base=base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
            size_limit=size_limit,
            paged_size=min(size_limit, 1000),
        )
        elapsed = (time.time() - t0) * 1000
        if not ok:
            logger.error("[AD] Search failed (%.1f ms): %s", elapsed, conn.result)
            return []

        logger.info("[AD] Search ok (%.1f ms). entries=%d", elapsed, len(conn.entries))
        return conn.entries

    @staticmethod
    def _escape(s: str) -> str:
        return escape_filter_chars(s or "")

    # ---------------------------
    # USERS
    # ---------------------------
    def search_users(self, query: str, size_limit: int = 100):
        q = self._escape(query)
        # Search by common attributes
        f = (
            f"(&(objectCategory=Person)(objectClass=User)"
            f"(|(sAMAccountName={q}*)(userPrincipalName={q}*)(mail={q}*)(displayName={q}*)(givenName={q}*)(sn={q}*)))"
        )
        return self._search(self.cfg.base_dn, f, size_limit=size_limit)

    def get_user_by_dn(self, dn: str):
        f = f"(&(objectCategory=Person)(objectClass=User)(distinguishedName={self._escape(dn)}))"
        res = self._search(self.cfg.base_dn, f, size_limit=1)
        return res[0] if res else None

    def reset_password(self, dn: str, new_password: str, force_change_next_logon: bool = False) -> bool:
        """
        Uses the Microsoft password modify extended operation.
        """
        conn = self._ensure_conn()
        logger.info("[AD] Reset password for dn=%s force_change_next_logon=%s", dn, force_change_next_logon)
        try:
            ok = conn.extend.microsoft.modify_password(dn, new_password)
            if not ok:
                logger.error("[AD] modify_password failed: %s", conn.result)
                return False
            if force_change_next_logon:
                conn.modify(dn, {"pwdLastSet": [(MODIFY_REPLACE, [0])]})
            else:
                conn.modify(dn, {"pwdLastSet": [(MODIFY_REPLACE, [-1])]})
            if conn.result["result"] != 0:
                logger.warning("[AD] pwdLastSet modify returned: %s", conn.result)
            return True
        except Exception as e:
            logger.exception("[AD] reset_password exception: %s", e)
            return False

    def unlock_user(self, dn: str) -> bool:
        conn = self._ensure_conn()
        logger.info("[AD] Unlock user dn=%s", dn)
        try:
            conn.modify(dn, {"lockoutTime": [(MODIFY_REPLACE, [0])]})
            if conn.result["result"] != 0:
                logger.error("[AD] unlock modify failed: %s", conn.result)
                return False
            return True
        except Exception as e:
            logger.exception("[AD] unlock_user exception: %s", e)
            return False

    def set_user_enabled(self, dn: str, enabled: bool) -> bool:
        """
        Toggle userAccountControl DISABLED bit (0x2).
        """
        conn = self._ensure_conn()
        logger.info("[AD] Set user enabled=%s dn=%s", enabled, dn)
        try:
            # Read current UAC
            ok = conn.search(dn, "(objectClass=*)", attributes=["userAccountControl"])
            if not ok or not conn.entries:
                logger.error("[AD] read userAccountControl failed: %s", conn.result)
                return False
            uac = int(conn.entries[0]["userAccountControl"].value)
            DISABLED = 0x2
            new_uac = (uac & ~DISABLED) if enabled else (uac | DISABLED)
            conn.modify(dn, {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]})
            if conn.result["result"] != 0:
                logger.error("[AD] set_user_enabled failed: %s", conn.result)
                return False
            return True
        except Exception as e:
            logger.exception("[AD] set_user_enabled exception: %s", e)
            return False

    def move_user(self, user_dn: str, new_ou_dn: str) -> bool:
        """
        Move a user to another OU (within the same domain).
        """
        conn = self._ensure_conn()
        logger.info("[AD] Move user dn=%s -> new_ou=%s", user_dn, new_ou_dn)
        try:
            # Extract current CN=... from the RDN
            rdn = user_dn.split(",")[0]
            ok = conn.modify_dn(user_dn, rdn, new_superior=new_ou_dn)
            if not ok:
                logger.error("[AD] modify_dn failed: %s", conn.result)
                return False
            return True
        except Exception as e:
            logger.exception("[AD] move_user exception: %s", e)
            return False

    def create_user(self, cn: str, parent_ou_dn: Optional[str], attributes: Dict[str, str],
                    initial_password: Optional[str] = None,
                    force_change_next_logon: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Create a new user under parent_ou_dn (or default_user_ou if None).
        Returns (ok, new_dn)
        """
        conn = self._ensure_conn()
        target_ou = parent_ou_dn or self.cfg.default_user_ou or self.cfg.base_dn
        new_dn = f"CN={cn},{target_ou}"
        logger.info("[AD] Create user cn=%s parent_ou=%s dn=%s", cn, target_ou, new_dn)
        try:
            # Basic attributes (merge with supplied)
            attrs = {
                "cn": cn,
                "displayName": attributes.get("displayName", cn),
                "givenName": attributes.get("givenName", ""),
                "sn": attributes.get("sn", ""),
                "name": attributes.get("name", cn),
                "userPrincipalName": attributes.get("userPrincipalName", ""),
                "sAMAccountName": attributes.get("sAMAccountName", ""),
                "mail": attributes.get("mail", ""),
                "userAccountControl": 0x0200 | 0x0800,  # NORMAL_ACCOUNT + PASSWD_NOTREQD (will reset below)
                **{k: v for k, v in attributes.items() if k not in {
                    "displayName", "givenName", "sn", "name", "userPrincipalName", "sAMAccountName", "mail"
                }}
            }
            ok = conn.add(new_dn, ["top", "person", "organizationalPerson", "user"], attrs)
            if not ok:
                logger.error("[AD] add user failed: %s", conn.result)
                return False, None

            # Set password if provided
            if initial_password:
                pwd_ok = conn.extend.microsoft.modify_password(new_dn, initial_password)
                if not pwd_ok:
                    logger.error("[AD] set initial password failed: %s", conn.result)
                    # still return created DN so caller can handle
                # Force change next logon?
                conn.modify(new_dn, {"pwdLastSet": [(MODIFY_REPLACE, [0 if force_change_next_logon else -1])]})

            # Finally, ensure account is enabled
            self.set_user_enabled(new_dn, True)

            return True, new_dn
        except Exception as e:
            logger.exception("[AD] create_user exception: %s", e)
            return False, None

    # ---------------------------
    # GROUPS
    # ---------------------------
    def search_groups(self, query: str, size_limit: int = 100):
        q = self._escape(query)
        f = f"(&(objectClass=group)(|(cn={q}*)(name={q}*)(sAMAccountName={q}*)))"
        return self._search(self.cfg.base_dn, f, size_limit=size_limit)

    def get_group_by_dn(self, dn: str):
        f = f"(&(objectClass=group)(distinguishedName={self._escape(dn)}))"
        res = self._search(self.cfg.base_dn, f, size_limit=1)
        return res[0] if res else None

    def list_group_members_dns(self, group_dn: str, size_limit: int = 2000) -> List[str]:
        conn = self._ensure_conn()
        logger.info("[AD] List members group_dn=%s", group_dn)
        ok = conn.search(group_dn, "(objectClass=*)", attributes=["member"])
        if not ok or not conn.entries:
            logger.error("[AD] list_group_members failed: %s", conn.result)
            return []
        members = conn.entries[0]["member"].values if "member" in conn.entries[0] else []
        return list(members)

    def add_user_to_group(self, user_dn: str, group_dn: str) -> bool:
        conn = self._ensure_conn()
        logger.info("[AD] Add user to group user_dn=%s group_dn=%s", user_dn, group_dn)
        try:
            ok = conn.modify(group_dn, {"member": [(MODIFY_ADD, [user_dn])]})
            if not ok and conn.result.get("result") == 68:  # Already exists
                logger.info("[AD] user already in group")
                return True
            if not ok:
                logger.error("[AD] add_user_to_group failed: %s", conn.result)
                return False
            return True
        except Exception as e:
            logger.exception("[AD] add_user_to_group exception: %s", e)
            return False

    def remove_user_from_group(self, user_dn: str, group_dn: str) -> bool:
        conn = self._ensure_conn()
        logger.info("[AD] Remove user from group user_dn=%s group_dn=%s", user_dn, group_dn)
        try:
            ok = conn.modify(group_dn, {"member": [(MODIFY_DELETE, [user_dn])]})
            if not ok and conn.result.get("result") == 16:  # No such attribute / not a member
                logger.info("[AD] user not a member of group")
                return True
            if not ok:
                logger.error("[AD] remove_user_from_group failed: %s", conn.result)
                return False
            return True
        except Exception as e:
            logger.exception("[AD] remove_user_from_group exception: %s", e)
            return False

    # ---------------------------
    # COMPUTERS
    # ---------------------------
    def search_computers(self, query: str, size_limit: int = 100):
        q = self._escape(query)
        f = f"(&(objectCategory=Computer)(|(cn={q}*)(name={q}*)(dNSHostName={q}*)))"
        return self._search(self.cfg.base_dn, f, size_limit=size_limit)

    def get_computer_by_dn(self, dn: str):
        f = f"(&(objectCategory=Computer)(distinguishedName={self._escape(dn)}))"
        res = self._search(self.cfg.base_dn, f, size_limit=1)
        return res[0] if res else None

    # ---------------------------
    # OUs
    # ---------------------------
    def list_ous(self, under_dn: Optional[str] = None, size_limit: int = 2000):
        f = "(objectClass=organizationalUnit)"
        return self._search(under_dn or self.cfg.base_dn, f, size_limit=size_limit)