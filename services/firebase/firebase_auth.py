import pyrebase
from core.config import FIREBASE_CONFIG

# فائر بیس انیشلائزیشن
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
auth = firebase.auth()

# یہ وہ فنکشن ہے جو آپ امپورٹ کرنے کی کوشش کر رہے ہیں
def login_user(email, password):
    try:
        # فائر بیس کے ذریعے لاگ ان
        user = auth.sign_in_with_email_and_password(email, password)
        return {"success": True, "user": user}
    except Exception as e:
        print(f"Login Error: {e}")
        return {"success": False, "error": str(e)}
