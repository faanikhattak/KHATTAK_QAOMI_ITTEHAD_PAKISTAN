# ================================================================
#  services/notifications.py
#  In-app Notification Service for Khattak Qomi Etehad Pakistan
# ================================================================

import asyncio
from typing import Optional
from supabase import Client

from core.theme import Theme 
# ========================
# NOTIFICATION TYPES
# ========================
class NotifType:
    BLOOD_REQUEST         = "blood_request"
    DONOR_ACCEPTED        = "donor_accepted"
    DONATION_CONFIRMED    = "donation_confirmed"
    NEW_REQUEST_ADMIN     = "new_request_admin"
    ELIGIBILITY_RESTORED  = "eligibility_restored"
    REQUEST_EXPIRED       = "request_expired"
    GENERAL               = "general"


# ========================
# FETCH NOTIFICATIONS
# ========================
async def fetch_notifications(
    supabase_client: Client,
    user_id: str,
    limit: int = 30,
) -> list[dict]:
    """
    User ki sari notifications fetch karo (latest first).
    """
    try:
        def _fetch():
            return (
                supabase_client
                .table("notifications")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        res = await asyncio.to_thread(_fetch)
        return res.data or []
    except Exception as ex:
        print(f"[NOTIF] fetch error: {ex}")
        return []


# ========================
# UNREAD COUNT
# ========================
async def fetch_unread_count(supabase_client, user_id):
    try:
        print(f"[NOTIF] fetch_unread_count called — user_id='{user_id}'")
        def _count():
            return (
                supabase_client
                .table("notifications")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("is_read", False)
                .execute()
            )
        res = await asyncio.to_thread(_count)
        print(f"[NOTIF] raw result — count={res.count}, data={res.data}")
        return res.count or 0
    except Exception as ex:
        import traceback
        print(f"[NOTIF] fetch_unread_count FULL ERROR:\n{traceback.format_exc()}")
        return 0


# ========================
# MARK AS READ
# ========================
async def mark_notification_read(
    supabase_client: Client,
    notification_id: int,
) -> bool:
    """Ek notification ko read mark karo."""
    try:
        def _mark():
            from datetime import datetime, timezone
            return (
                supabase_client
                .table("notifications")
                .update({"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", notification_id)
                .execute()
            )
        await asyncio.to_thread(_mark)
        return True
    except Exception as ex:
        print(f"[NOTIF] mark read error: {ex}")
        return False


async def mark_all_read(
    supabase_client: Client,
    user_id: str,
) -> bool:
    """User ki sari notifications read mark karo."""
    try:
        def _mark_all():
            from datetime import datetime, timezone
            return (
                supabase_client
                .table("notifications")
                .update({"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()})
                .eq("user_id", user_id)
                .eq("is_read", False)
                .execute()
            )
        await asyncio.to_thread(_mark_all)
        return True
    except Exception as ex:
        print(f"[NOTIF] mark all read error: {ex}")
        return False


# ========================
# INSERT NOTIFICATION
# ========================
async def insert_notification(
    supabase_client: Client,
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    title_urdu: str = "",
    body_urdu: str = "",
    request_id: Optional[int] = None,
    donation_id: Optional[str] = None,
) -> bool:
    """
    Ek nai notification insert karo.
    Donor ko, requester ko, ya admin ko — user_id pass karo.
    """
    try:
        payload = {
            "user_id":     user_id,
            "type":        notif_type,
            "title":       title,
            "message":     message,
            "title_urdu":  title_urdu or "",
            "body_urdu":   body_urdu or "",
            "is_read":     False,
        }
        if request_id:
            payload["request_id"] = request_id
        if donation_id:
            payload["donation_id"] = donation_id

        def _insert():
            return supabase_client.table("notifications").insert(payload).execute()

        await asyncio.to_thread(_insert)
        return True
    except Exception as ex:
        print(f"[NOTIF] insert error: {ex}")
        return False


# ========================
# NOTIFY MATCHING DONORS
# ========================
async def notify_matching_donors(
    supabase_client: Client,
    blood_group: str,
    province: str,
    city: str,
    request_id: int,
    requester_name: str,
    hospital: str,
    urgency: str = "medium",
) -> int:
    """
    Blood request ke liye matching donors ko notify karo.
    Returns: kitne donors ko notification gayi
    """
    try:
        # Step 1: Matching donors dhundo
        def _find_donors():
            return (
                supabase_client
                .table("profile")
                .select("id, full_name, blood_group, city, province, is_eligible_donor, is_available")
                .eq("blood_group", blood_group)
                .eq("city", city)
                .eq("is_eligible_donor", True)
                .eq("is_available", True)
                .eq("is_active", True)
                .execute()
            )

        res = await asyncio.to_thread(_find_donors)
        donors = res.data or []

        if not donors:
            # Same city mein nahi mila — same province try karo
            def _find_province():
                return (
                    supabase_client
                    .table("profile")
                    .select("id, full_name, blood_group, city, province, is_eligible_donor, is_available")
                    .eq("blood_group", blood_group)
                    .eq("province", province)
                    .eq("is_eligible_donor", True)
                    .eq("is_available", True)
                    .eq("is_active", True)
                    .execute()
                )
            res2 = await asyncio.to_thread(_find_province)
            donors = res2.data or []

        if not donors:
            print(f"[NOTIF] No matching donors for {blood_group} in {city}/{province}")
            return 0

        # Urgency label
        urgency_labels = {
            "low":      "کم ضروری",
            "medium":   "درمیانہ ضروری",
            "high":     "ضروری — آج چاہیے",
            "critical": "⚠️ ہنگامی — ابھی چاہیے",
        }
        urgency_ur = urgency_labels.get(urgency, "ضروری")

        # Step 2: Har donor ko notification bhejo
        count = 0
        for donor in donors:
            donor_id = donor.get("id")
            if not donor_id:
                continue

            success = await insert_notification(
                supabase_client=supabase_client,
                user_id=str(donor_id),
                notif_type=NotifType.BLOOD_REQUEST,
                title=f"🩸 Blood Needed: {blood_group}",
                message=f"{requester_name} needs {blood_group} blood at {hospital}, {city}. Urgency: {urgency}",
                title_urdu=f"🩸 خون درکار ہے: {blood_group}",
                body_urdu=f"{requester_name} کو {hospital}، {city} میں {blood_group} خون چاہیے۔ {urgency_ur}",
                request_id=request_id,
            )
            if success:
                count += 1

        print(f"[NOTIF] Notified {count}/{len(donors)} donors for request #{request_id}")
        return count

    except Exception as ex:
        print(f"[NOTIF] notify_matching_donors error: {ex}")
        return 0


# ========================
# NOTIFY REQUESTER
# ========================
async def notify_requester_donor_accepted(
    supabase_client: Client,
    requester_id: str,
    donor_name: str,
    donor_phone: str,
    request_id: int,
) -> bool:
    """Requester ko batao ke donor ne accept kar liya."""
    return await insert_notification(
        supabase_client=supabase_client,
        user_id=requester_id,
        notif_type=NotifType.DONOR_ACCEPTED,
        title="✅ Donor Found!",
        message=f"{donor_name} has accepted your blood request. Contact: {donor_phone}",
        title_urdu="✅ ڈونر مل گیا!",
        body_urdu=f"{donor_name} نے آپ کی درخواست قبول کر لی۔ رابطہ: {donor_phone}",
        request_id=request_id,
    )


# ========================
# NOTIFY DONATION CONFIRMED
# ========================
async def notify_donation_confirmed(
    supabase_client: Client,
    donor_id: str,
    requester_id: str,
    blood_group: str,
    request_id: int,
) -> None:
    """Dono ko batao ke donation confirm ho gayi."""
    await insert_notification(
        supabase_client=supabase_client,
        user_id=donor_id,
        notif_type=NotifType.DONATION_CONFIRMED,
        title="🎉 Donation Confirmed!",
        message=f"Your {blood_group} blood donation has been confirmed. JazakAllah Khair!",
        title_urdu="🎉 عطیہ خون تصدیق ہو گیا!",
        body_urdu=f"آپ کا {blood_group} خون کا عطیہ تصدیق ہو گیا۔ جزاک اللہ خیر!",
        request_id=request_id,
    )
    await insert_notification(
        supabase_client=supabase_client,
        user_id=requester_id,
        notif_type=NotifType.DONATION_CONFIRMED,
        title="🩸 Blood Received!",
        message="Blood donation has been confirmed. May Allah grant you health!",
        title_urdu="🩸 خون مل گیا!",
        body_urdu="خون کا عطیہ تصدیق ہو گیا۔ اللہ آپ کو صحت عطا فرمائے!",
        request_id=request_id,
    )


# ========================
# NOTIFY ADMIN — NEW REQUEST
# ========================
async def notify_area_admins(
    supabase_client: Client,
    province: str,
    city: str,
    blood_group: str,
    requester_name: str,
    request_id: int,
) -> int:
    """Us area ke admins ko notify karo jahan request aayi."""
    try:
        def _find_admins():
            return (
                supabase_client
                .table("profile")
                .select("id")
                .eq("city", city)
                .eq("province", province)
                .in_("role", ["admin", "head_admin"])
                .eq("is_active", True)
                .execute()
            )
        res = await asyncio.to_thread(_find_admins)
        admins = res.data or []

        if not admins:
            # Fallback: all head_admins
            def _find_head():
                return (
                    supabase_client
                    .table("profile")
                    .select("id")
                    .eq("role", "head_admin")
                    .execute()
                )
            res2 = await asyncio.to_thread(_find_head)
            admins = res2.data or []

        count = 0
        for admin in admins:
            success = await insert_notification(
                supabase_client=supabase_client,
                user_id=str(admin["id"]),
                notif_type=NotifType.NEW_REQUEST_ADMIN,
                title=f"🆕 New Blood Request: {blood_group}",
                message=f"{requester_name} needs {blood_group} in {city}, {province}",
                title_urdu=f"🆕 نئی درخواست خون: {blood_group}",
                body_urdu=f"{requester_name} کو {city}، {province} میں {blood_group} خون درکار ہے",
                request_id=request_id,
            )
            if success:
                count += 1

        return count

    except Exception as ex:
        print(f"[NOTIF] notify_area_admins error: {ex}")
        return 0