# pages/user/home.py
import flet as ft
from home_module.home import view as _home_view

def view(page: ft.Page) -> ft.View:
    # Any pre-flight setup goes here (optional)
    # e.g. page.title = "Home"
    return _home_view(page)  

