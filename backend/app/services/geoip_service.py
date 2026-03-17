# backend/app/services/geoip_service.py

import requests
from functools import lru_cache

@lru_cache(maxsize=5000)
def lookup_geoip(ip: str) -> dict:
    if not ip:
        return {}

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,regionName,zip,lat,lon,isp,org,as,query"
        r = requests.get(url, timeout=3)
        if r.status_code != 200:
            return {}

        data = r.json()
        if data.get("status") != "success":
            return {}
        return data
    except Exception:
        return {}