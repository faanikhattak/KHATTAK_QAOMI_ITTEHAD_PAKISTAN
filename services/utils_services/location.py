import traceback

import requests
import flet as ft

try:
    import flet_geolocator as fg
except ImportError:
    fg = None


# ════════════════════════════════════════════════════════════════
#  FEATURE FLAG
# ════════════════════════════════════════════════════════════════
# Temporarily disabled: the Geolocator Flutter plugin isn't bundled
# into the plain `python home.py` desktop preview (only `flet run` /
# `flet build` resolve extension controls properly). Flip this back
# to True once local testing goes through `flet run` with
# flet-geolocator declared in pyproject.toml.
ENABLE_GPS: bool = False


# ════════════════════════════════════════════════════════════════
#  FALLBACK — coarse, IP-based (city-level accuracy only)
# ════════════════════════════════════════════════════════════════
def get_location_by_ip():
    """
    Coarse fallback location based on the device's public IP.
    Accuracy is city-level at best and can be wrong on VPN/mobile
    data routed through a different region. Use ONLY when GPS
    permission is denied or location services are unavailable.
    """
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5).json()
        if r.get("status") == "fail":
            print("[LOCATION] ip-api lookup failed:", r.get("message"))
            return 0.0, 0.0
        return r["lat"], r["lon"]
    except Exception as ex:
        print("[LOCATION] IP lookup error:", ex)
        return 0.0, 0.0


# ════════════════════════════════════════════════════════════════
#  PRIMARY — accurate device GPS (requires permission)
# ════════════════════════════════════════════════════════════════
def add_geolocator(page: ft.Page):
    """
    Creates (or reuses) the Geolocator control on the page overlay.
    Returns None (and does NOT touch page.overlay) while ENABLE_GPS
    is False, so the "Unknown control: Geolocator" crash can't
    happen during local `python home.py` testing.
    """
    if not ENABLE_GPS:
        return None

    existing = getattr(page, "_geolocator_ref", None)
    if existing is not None:
        return existing

    geo = fg.Geolocator()
    page.overlay.append(geo)
    page._geolocator_ref = geo
    return geo


async def get_location_gps(page: ft.Page, geo):
    """
    Attempts to get precise device GPS coordinates.
    Returns (lat, lon) tuple, or None if disabled / permission
    denied / location services disabled / any error occurred.
    """
    if not ENABLE_GPS or geo is None:
        return None

    try:
        status = await geo.get_permission_status()
        if status == fg.GeolocatorPermissionStatus.DENIED:
            status = await geo.request_permission()

        if status in (
            fg.GeolocatorPermissionStatus.DENIED,
            fg.GeolocatorPermissionStatus.DENIED_FOREVER,
        ):
            print("[LOCATION] GPS permission denied")
            return None

        if not await geo.is_location_service_enabled():
            print("[LOCATION] device location services are off")
            return None

        pos = await geo.get_current_position()
        print(f"[LOCATION] GPS ok: lat={pos.latitude}, lng={pos.longitude}")
        return pos.latitude, pos.longitude

    except Exception:
        print("[LOCATION] GPS error:")
        traceback.print_exc()
        return None


# ════════════════════════════════════════════════════════════════
#  ENTRY POINT — GPS first (if enabled), IP fallback otherwise
# ════════════════════════════════════════════════════════════════
async def get_location(page: ft.Page, geo):
    """
    Primary entry point for the app: tries accurate GPS first (when
    ENABLE_GPS is True), gracefully falls back to coarse IP-based
    location otherwise.
    """
    gps = await get_location_gps(page, geo)
    if gps:
        return gps

    print("[LOCATION] falling back to IP-based location")
    return get_location_by_ip()

















# import traceback

# import requests
# import flet as ft



# # ════════════════════════════════════════════════════════════════
# #  FEATURE FLAG
# # ════════════════════════════════════════════════════════════════
# # Temporarily disabled: the Geolocator Flutter plugin isn't bundled
# # into the plain `python home.py` desktop preview (only `flet run` /
# # `flet build` resolve extension controls properly). Flip this back
# # to True once local testing goes through `flet run` with
# # flet-geolocator declared in pyproject.toml.
# ENABLE_GPS: bool = False


# # ════════════════════════════════════════════════════════════════
# #  FALLBACK — coarse, IP-based (city-level accuracy only)
# # ════════════════════════════════════════════════════════════════
# def get_location_by_ip():
#     """
#     Coarse fallback location based on the device's public IP.
#     Accuracy is city-level at best and can be wrong on VPN/mobile
#     data routed through a different region. Use ONLY when GPS
#     permission is denied or location services are unavailable.
#     """
#     try:
#         r = requests.get("http://ip-api.com/json/", timeout=5).json()
#         if r.get("status") == "fail":
#             print("[LOCATION] ip-api lookup failed:", r.get("message"))
#             return 0.0, 0.0
#         return r["lat"], r["lon"]
#     except Exception as ex:
#         print("[LOCATION] IP lookup error:", ex)
#         return 0.0, 0.0


# # ════════════════════════════════════════════════════════════════
# #  PRIMARY — accurate device GPS (requires permission)
# # ════════════════════════════════════════════════════════════════
# def add_geolocator(page: ft.Page):
#     """
#     Creates (or reuses) the Geolocator control on the page overlay.
#     Returns None (and does NOT touch page.overlay) while ENABLE_GPS
#     is False, so the "Unknown control: Geolocator" crash can't
#     happen during local `python home.py` testing.
#     """
#     if not ENABLE_GPS:
#         return None

#     existing = getattr(page, "_geolocator_ref", None)
#     if existing is not None:
#         return existing

#     geo = fg.Geolocator()
#     page.overlay.append(geo)
#     page._geolocator_ref = geo
#     return geo


# async def get_location_gps(page: ft.Page, geo):
#     """
#     Attempts to get precise device GPS coordinates.
#     Returns (lat, lon) tuple, or None if disabled / permission
#     denied / location services disabled / any error occurred.
#     """
#     if not ENABLE_GPS or geo is None:
#         return None

#     try:
#         status = await geo.get_permission_status()
#         if status == fg.GeolocatorPermissionStatus.DENIED:
#             status = await geo.request_permission()

#         if status in (
#             fg.GeolocatorPermissionStatus.DENIED,
#             fg.GeolocatorPermissionStatus.DENIED_FOREVER,
#         ):
#             print("[LOCATION] GPS permission denied")
#             return None

#         if not await geo.is_location_service_enabled():
#             print("[LOCATION] device location services are off")
#             return None

#         pos = await geo.get_current_position()
#         print(f"[LOCATION] GPS ok: lat={pos.latitude}, lng={pos.longitude}")
#         return pos.latitude, pos.longitude

#     except Exception:
#         print("[LOCATION] GPS error:")
#         traceback.print_exc()
#         return None


# # ════════════════════════════════════════════════════════════════
# #  ENTRY POINT — GPS first (if enabled), IP fallback otherwise
# # ════════════════════════════════════════════════════════════════
# async def get_location(page: ft.Page, geo):
#     """
#     Primary entry point for the app: tries accurate GPS first (when
#     ENABLE_GPS is True), gracefully falls back to coarse IP-based
#     location otherwise.
#     """
#     gps = await get_location_gps(page, geo)
#     if gps:
#         return gps

#     print("[LOCATION] falling back to IP-based location")
#     return get_location_by_ip()