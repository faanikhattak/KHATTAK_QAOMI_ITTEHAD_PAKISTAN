# Simple global state (Flet apps ke liye best approach)

class AppState:
    user_id = None
    user_data = None
    is_admin = False

state = AppState()