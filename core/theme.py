import flet as ft

# ================================================================
# !! ACTIVE THEME CONTROL CONFIGURATION (TOP OF FILE) !!
# جو تھیم رکھنی ہو، اس کا کمنٹ (#) ہٹا دیں اور باقیوں کے آگے # لگا دیں:
# ================================================================
ACTIVE_THEME = "crimson"
#ACTIVE_THEME = "teal"
#ACTIVE_THEME = "royal"
# ACTIVE_THEME = "orange"
#ACTIVE_THEME = "charcoal"


# ================================================================
# 1. THEME PALETTES DATA DEFINITIONS
# ================================================================
_PALETTES = {
    "crimson": {
        "PRIMARY": "#E24B4A", "PRIMARY_DK": "#A32D2D", "PRIMARY_LT": "#FBEAEA", "PRIMARY_MD": "#F3C9C9",
        "GREEN": "#1D9E75", "TEAL": "#1D9E75", "BLUE": "#378ADD", "ORANGE": "#EF9F27", "RED": "#E24B4A", "PURPLE": "#7C4DFF",
        "BG": "#F5F5F7", "SURFACE": "#FFFFFF", "SURFACE_2": "#F1EEEF", "BORDER": "#E0E0E0",
        "TEXT": "#1C1C1E", "TEXT_SUB": "#6B6B70", "TEXT_HINT": "#9A9A9E", "TEXT_DARK": "#1C1C1E", "ON_SURFACE": "#1C1C1E"
    },
    "teal": {
        "PRIMARY": "#0F766E", "PRIMARY_DK": "#115E59", "PRIMARY_LT": "#F0FDFA", "PRIMARY_MD": "#CCFBF1",
        "GREEN": "#10B981", "TEAL": "#0F766E", "BLUE": "#2563EB", "ORANGE": "#D97706", "RED": "#EF4444", "PURPLE": "#6D28D9",
        "BG": "#F4F7F6", "SURFACE": "#FFFFFF", "SURFACE_2": "#E6ECEB", "BORDER": "#D1DEDC",
        "TEXT": "#0F172A", "TEXT_SUB": "#475569", "TEXT_HINT": "#94A3B8", "TEXT_DARK": "#0F172A", "ON_SURFACE": "#0F172A"
    },
    "royal": {
        "PRIMARY": "#1E40AF", "PRIMARY_DK": "#1E3A8A", "PRIMARY_LT": "#EFF6FF", "PRIMARY_MD": "#DBEAFE",
        "GREEN": "#16A34A", "TEAL": "#0D9488", "BLUE": "#1E40AF", "ORANGE": "#EA580C", "RED": "#DC2626", "PURPLE": "#7C3AED",
        "BG": "#F8FAFC", "SURFACE": "#FFFFFF", "SURFACE_2": "#F1F5F9", "BORDER": "#E2E8F0",
        "TEXT": "#0F172A", "TEXT_SUB": "#475569", "TEXT_HINT": "#94A3B8", "TEXT_DARK": "#0F172A", "ON_SURFACE": "#0F172A"
    },
    "orange": {
        "PRIMARY": "#D97706", "PRIMARY_DK": "#B45309", "PRIMARY_LT": "#FEF3C7", "PRIMARY_MD": "#FDE68A",
        "GREEN": "#15803D", "TEAL": "#0F766E", "BLUE": "#1D4ED8", "ORANGE": "#D97706", "RED": "#B91C1C", "PURPLE": "#6D28D9",
        "BG": "#FAFAF9", "SURFACE": "#FFFFFF", "SURFACE_2": "#F5F5F4", "BORDER": "#E7E5E4",
        "TEXT": "#1C1917", "TEXT_SUB": "#57534E", "TEXT_HINT": "#A8A29E", "TEXT_DARK": "#1C1917", "ON_SURFACE": "#1C1917"
    },
    "charcoal": {
        "PRIMARY": "#27272A", "PRIMARY_DK": "#18181B", "PRIMARY_LT": "#F4F4F5", "PRIMARY_MD": "#E4E4E7",
        "GREEN": "#10B981", "TEAL": "#14B8A6", "BLUE": "#3B82F6", "ORANGE": "#F59E0B", "RED": "#EF4444", "PURPLE": "#8B5CF6",
        "BG": "#FAFAFA", "SURFACE": "#FFFFFF", "SURFACE_2": "#F4F4F5", "BORDER": "#E4E4E7",
        "TEXT": "#09090B", "TEXT_SUB": "#71717A", "TEXT_HINT": "#A1A1AA", "TEXT_DARK": "#09090B", "ON_SURFACE": "#09090B"
    }
}

_c = _PALETTES.get(ACTIVE_THEME, _PALETTES["crimson"])

# ================================================================
# 2. THE CENTRAL SOURCE OF TRUTH (CLASS BASED)
# ================================================================
class Theme:
    PRIMARY     = _c["PRIMARY"]
    PRIMARY_DK  = _c["PRIMARY_DK"]
    PRIMARY_LT  = _c["PRIMARY_LT"]
    PRIMARY_MD  = _c["PRIMARY_MD"]

    GREEN = _c["GREEN"]; TEAL = _c["TEAL"]; BLUE = _c["BLUE"]
    ORANGE = _c["ORANGE"]; RED = _c["RED"]; PURPLE = _c["PURPLE"]
    BG = _c["BG"]; SURFACE = _c["SURFACE"]; SURFACE_2 = _c["SURFACE_2"]; BORDER = _c["BORDER"]
    TEXT = _c["TEXT"]; TEXT_SUB = _c["TEXT_SUB"]; TEXT_HINT = _c["TEXT_HINT"]
    TEXT_DARK = _c["TEXT_DARK"]; ON_SURFACE = _c["ON_SURFACE"]
    
    FIELD_WIDTH = 400; CARD_WIDTH = 434; RADIUS_SM = 8; RADIUS_MD = 14; RADIUS_LG = 18
    
    STATUS_COLORS = {"pending": ("#FFF3E0", "#B26A00"), "matching": ("#E3F2FD", "#1565C0"), "in_progress": ("#EDE7F6", "#5E35B1"), "fulfilled": ("#E8F5E9", "#2E7D32"), "cancelled": ("#F0F0F0", "#757575"), "expired": ("#F0F0F0", "#757575")}
    STATUS_LABELS = {"pending": "⏳ Pending", "matching": "🔍 Matching", "in_progress": "✅ Donor Found", "fulfilled": "🎉 Fulfilled", "cancelled": "❌ Cancelled", "expired": "⌛ Expired"}
    URGENCY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}

    @classmethod
    def field_style(cls, width: int | None = None) -> dict:
        return dict(border_radius=cls.RADIUS_MD, focused_border_color=cls.PRIMARY, border_color=cls.BORDER, text_size=14, color=cls.TEXT, label_style=ft.TextStyle(color=cls.TEXT_SUB), bgcolor=cls.SURFACE, width=width or cls.FIELD_WIDTH)

    @classmethod
    def dropdown_style(cls, width: int | None = None) -> dict:
        return dict(border_radius=cls.RADIUS_MD, focused_border_color=cls.PRIMARY, border_color=cls.BORDER, color=cls.TEXT, bgcolor=cls.SURFACE, width=width or cls.FIELD_WIDTH)

    @classmethod
    def primary_button_style(cls, bgcolor: str | None = None) -> ft.ButtonStyle:
        return ft.ButtonStyle(color="white", bgcolor=bgcolor or cls.PRIMARY, shape=ft.RoundedRectangleBorder(radius=13), elevation=4)

    @classmethod
    def muted_text_style(cls) -> ft.ButtonStyle:
        return ft.ButtonStyle(color=cls.TEXT_SUB)

    @classmethod
    def card_container(cls, content, width: int | None = None) -> ft.Container:
        return ft.Container(bgcolor=cls.SURFACE, border_radius=cls.RADIUS_LG, padding=ft.padding.symmetric(horizontal=20, vertical=18), width=width or cls.CARD_WIDTH, content=content)

    @classmethod
    def status_badge(cls, status: str, override_label: str | None = None, override_colors: tuple | None = None) -> ft.Container:
        bg, tc = override_colors or cls.STATUS_COLORS.get(status, ("#412402", "#FAC775"))
        label = override_label or cls.STATUS_LABELS.get(status, status.capitalize())
        return ft.Container(content=ft.Text(label, size=10, weight=ft.FontWeight.W_700, color=tc), bgcolor=bg, padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=cls.RADIUS_SM)

    @classmethod
    def appbar(cls, title_en: str, title_ur: str, on_back=None, actions=None) -> ft.AppBar:
        return ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color="white", on_click=on_back), title=ft.Column([ft.Text(title_en, size=16, weight=ft.FontWeight.BOLD, color="white"), ft.Text(title_ur, size=11, color=cls.PRIMARY_MD)], spacing=0), bgcolor=cls.PRIMARY, actions=actions or [])

    @classmethod
    def home_fab(cls, page: ft.Page, is_home: bool = False, route: str = "/home") -> ft.FloatingActionButton:
        def _go_home(e=None):
            if is_home: return
            try: page.go(route)
            except Exception as ex: print(f"[THEME] home_fab navigation error: {ex}")
        return ft.FloatingActionButton(icon=ft.Icons.HOME_ROUNDED, bgcolor=cls.PRIMARY_MD if is_home else cls.PRIMARY, foreground_color="white", tooltip="Home | ہوم", mini=False, shape=ft.CircleBorder(), on_click=_go_home, disabled=is_home)

    @classmethod
    def home_bar_button(cls, page: ft.Page, is_home: bool = False, route: str = "/home") -> ft.IconButton:
        def _go_home(e=None):
            if is_home: return
            try: page.go(route)
            except Exception as ex: print(f"[THEME] home_bar_button navigation error: {ex}")
        return ft.IconButton(icon=ft.Icons.HOME_ROUNDED, icon_color="#FFFFFF80" if is_home else "white", icon_size=24, tooltip="Already home" if is_home else "Home | ہوم", on_click=_go_home, disabled=is_home)


# ================================================================
# 3. LOWERCASE T DICTIONARY AUTO-GENERATOR FOR BACKWARD COMPATIBILITY
# ================================================================
class _ThemeTokens(dict):
    def __getattr__(self, name):
        try: return self[name]
        except KeyError: raise AttributeError(name)
    def __setattr__(self, name, value): self[name] = value

def _build_token_dict(cls) -> _ThemeTokens:
    tokens = _ThemeTokens()
    for attr_name in dir(cls):
        if attr_name.isupper() and not attr_name.startswith("_"):
            value = getattr(cls, attr_name)
            if isinstance(value, (str, int, float)):
                tokens[attr_name.lower()] = value
    return tokens

T = _build_token_dict(Theme)