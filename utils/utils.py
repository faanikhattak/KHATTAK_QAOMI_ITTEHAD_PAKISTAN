import flet as ft

def get_logo_control(page: ft.Page, width=52, height=52):
    # session سے لوگو حاصل کریں
    logo_url = page.session.get("org_logo_url") 
    
    return ft.Container(
        width=width, height=height, 
        border_radius=26,
        bgcolor="white", # لوگو کے پیچھے سفید بیک گراؤنڈ
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Image(
            src=logo_url if logo_url and logo_url != "None" else "logo.png", # اپنی ڈیفالٹ فائل کا نام دیں
            fit=ft.ImageFit.CONTAIN,
            width=width,
            height=height,
        )
    )