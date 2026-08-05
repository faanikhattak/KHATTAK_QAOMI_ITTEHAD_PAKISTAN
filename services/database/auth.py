#### new claud



from services.db import supabase
import flet as ft

# ================================================================
#  auth.py  –  Authentication & Session Management
#  ─────────────────────────────────────────────────────────────
#  یہ فائل login، logout اور session کا انتظام کرتی ہے۔
#  Functions:
#   • get_current_user()   → موجودہ user کی معلومات
#   • get_user_profile()   → profiles table سے profile
#   • get_user_role()      → user کا role (admin/donor/member)
#   • is_email_verified()  → Email تصدیق ہوئی؟
#   • is_approved()        → admin نے منظور کیا؟
#   • logout()             → session ختم کرنا
#   • save_session()       → session محفوظ کرنا
#   • load_session()       → session لوڈ کرنا
#   • auth_guard()         → page protect کرنا
# ================================================================


# ── موجودہ login user ──────────────────────────────────────────
def get_current_user():
    """
    Supabase سے موجودہ login user لاتا ہے۔
    اگر login نہ ہو تو None لوٹاتا ہے۔
    """
    try:
        res = supabase.auth.get_user()
        return res.user if res else None
    except Exception:
        return None


# ── Profiles table سے پروفائل ─────────────────────────────────
def get_user_profile(user_id: str) -> dict | None:
    """
    Supabase profiles table سے user کی پروفائل لاتا ہے۔
    user_id: Supabase auth user UUID
    """
    try:
        res = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return res.data if res else None
    except Exception:
        return None


# ── User کا role ───────────────────────────────────────────────
def get_user_role(user_id: str) -> str:
    """
    user کا role لوٹاتا ہے:
      "admin"  → ایڈمن
      "donor"  → ڈونر
      "member" → عام ممبر (default)
    """
    profile = get_user_profile(user_id)
    if profile:
        return profile.get("role", "member")
    return "member"


# ── Email تصدیق چیک ────────────────────────────────────────────
def is_email_verified(user_id: str) -> bool:
    """
    Email تصدیق ہوئی ہے یا نہیں۔
    profiles table میں email_verified column چیک کرتا ہے۔
    """
    profile = get_user_profile(user_id)
    if profile:
        return bool(profile.get("email_verified", False))
    return False


# ── Admin منظوری چیک ───────────────────────────────────────────
def is_approved(user_id: str) -> bool:
    """
    Admin نے ممبر کو منظور کیا ہے یا نہیں۔
    profiles table میں is_approved column چیک کرتا ہے۔
    """
    profile = get_user_profile(user_id)
    if profile:
        return bool(profile.get("is_approved", False))
    return False


# ── Session محفوظ کرنا ─────────────────────────────────────────
def save_session(page: ft.Page, user_id: str, email: str, role: str):
    """
    Login کے بعد session page.client_storage میں محفوظ کرتا ہے۔
    یہ app بند ہونے کے بعد بھی باقی رہتا ہے۔
    """
    try:
        page.client_storage.set("supabase_session", {
            "user_id": user_id,
            "email":   email,
            "role":    role,
        })
    except Exception:
        pass


# ── Session لوڈ کرنا ───────────────────────────────────────────
def load_session(page: ft.Page) -> dict | None:
    """
    پہلے سے محفوظ session لوڈ کرتا ہے۔
    اگر session نہ ہو تو None لوٹاتا ہے۔
    """
    try:
        return page.client_storage.get("supabase_session")
    except Exception:
        return None


# ── Session ختم کرنا ───────────────────────────────────────────
def logout(page: ft.Page):
    """
    Supabase سے sign out کرتا ہے اور session صاف کرتا ہے۔
    پھر login page پر بھیجتا ہے۔
    """
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    try:
        page.client_storage.remove("supabase_session")
    except Exception:
        pass
    page.go("/login")


# ── Page Guard ─────────────────────────────────────────────────
def auth_guard(page: ft.Page, required_role: str = "member") -> bool:
    """
    Page کو protect کرتا ہے۔
    بغیر login یا بغیر permission کے redirect کرتا ہے۔

    required_role:
      "member" → کوئی بھی login user دیکھ سکتا ہے
      "donor"  → صرف donor اور admin
      "admin"  → صرف admin

    Returns:
      True  → access مل گیا
      False → redirect ہو گیا
    """
    # Session چیک
    session = load_session(page)
    if not session:
        page.go("/login")
        return False

    user = get_current_user()
    if not user:
        page.go("/login")
        return False

    user_id = user.id

    # Email verify چیک
    if not is_email_verified(user_id):
        page.go("/verification")
        return False

    # Role چیک
    role = get_user_role(user_id)
    role_levels = {"member": 1, "donor": 2, "admin": 3}

    if role_levels.get(role, 0) < role_levels.get(required_role, 1):
        # کافی permission نہیں — home page پر بھیجیں
        page.go("/")
        return False

    return True


# ── Role سے Home Route ──────────────────────────────────────────
def get_home_route(role: str) -> str:
    """
    Role کے مطابق home route لوٹاتا ہے۔
      admin  → /admin
      donor  → /donor
      member → /
    """
    routes = {
        "admin":  "/admin",
        "donor":  "/donor",
        "member": "/",
    }
    return routes.get(role, "/")




