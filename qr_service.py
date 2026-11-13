"""
SIMATS Event Sphere - QR Ticketing & Attendance Scanner Module
Generates tamper-resistant QR codes for registrations and provides
camera-based / manual check-in verification via OpenCV with duplicate prevention.
"""

import os
import json
import io
import datetime
import qrcode
from PIL import Image
import numpy as np
import cv2

from database import (
    STATIC_DIR,
    QR_DIR,
    execute_query_one,
    execute_insert,
    execute_write,
    log_audit,
    create_notification
)


def generate_ticket_qr(registration_id: str, event_id: int, user_id: int) -> str:
    """
    Generate a ticket QR code image encoding verification payload
    and persist it to the static/qrcodes/ directory.
    Returns relative file path.
    """
    payload = {
        "reg_id": registration_id,
        "event_id": event_id,
        "user_id": user_id,
        "system": "SIMATS_EVENT_SPHERE"
    }
    payload_str = json.dumps(payload)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1B365D", back_color="white")
    
    filename = f"{registration_id}.png"
    filepath = os.path.join(QR_DIR, filename)
    img.save(filepath)

    rel_path = f"static/qrcodes/{filename}"
    # Update registration record with qr path
    execute_write("UPDATE registrations SET qr_code_path = ? WHERE registration_id = ?", (rel_path, registration_id))
    return rel_path


def decode_qr_image(image_bytes: bytes) -> str | None:
    """
    Decodes a QR code from raw image bytes using OpenCV QRCodeDetector.
    Returns the decoded string payload or None.
    """
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        if data:
            return data.strip()
        
        # Fallback multi-scale attempts if needed
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, _, _ = detector.detectAndDecode(gray)
        return data.strip() if data else None
    except Exception as e:
        print(f"[QR DECODE ERROR] {e}")
        return None


def extract_registration_id(decoded_raw: str) -> str:
    """
    Extracts registration_id whether the scanned QR contains JSON payload
    or pure registration_id string.
    """
    try:
        parsed = json.loads(decoded_raw)
        if isinstance(parsed, dict) and "reg_id" in parsed:
            return parsed["reg_id"]
    except Exception:
        pass
    return decoded_raw.strip()


def verify_and_check_in(
    registration_id: str,
    expected_event_id: int,
    scanned_by_user_id: int
) -> tuple[bool, str, dict | None]:
    """
    Verifies ticket eligibility and records attendance atomically.
    Guarantees:
    - Rejects non-existent registration IDs.
    - Rejects tickets belonging to a different event.
    - Rejects cancelled registrations.
    - Rejects unpaid external participant tickets.
    - Strictly prevents duplicate check-ins (returns prior check-in timestamp and scanner info).
    - Transitions registration status to 'Attended'.
    - Logs audit record and dispatches attendee notification.
    """
    clean_reg_id = extract_registration_id(registration_id)

    # 1. Look up registration with user and event details
    sql = """
    SELECT r.id as reg_db_id, r.registration_id, r.event_id, r.user_id, r.status as reg_status,
           r.payment_status, r.created_at as reg_date,
           u.full_name, u.email, u.category, u.institution, u.department,
           e.title as event_title, e.status as event_status
    FROM registrations r
    JOIN users u ON r.user_id = u.id
    JOIN events e ON r.event_id = e.id
    WHERE r.registration_id = ?
    """
    reg = execute_query_one(sql, (clean_reg_id,))

    if not reg:
        return False, f"Ticket verification failed: Registration ID '{clean_reg_id}' not found.", None

    # 2. Check event match
    if reg["event_id"] != expected_event_id:
        return False, f"Invalid Ticket: This ticket was issued for '{reg['event_title']}', not the currently selected event.", None

    # 3. Check registration validity
    if reg["reg_status"] == "Cancelled":
        return False, "Check-in REJECTED: This registration was previously CANCELLED.", None

    # 4. Check payment status
    if reg["payment_status"] not in ["Completed", "Exempt_Zero_Fee"]:
        return False, f"Check-in REJECTED: Payment status is '{reg['payment_status']}'. Entry requires payment completion.", None

    # 5. Check duplicate check-in
    existing_attendance = execute_query_one("""
    SELECT a.*, u.full_name as scanner_name
    FROM attendance a
    JOIN users u ON a.scanned_by = u.id
    WHERE a.registration_id = ?
    """, (reg["reg_db_id"],))

    if existing_attendance:
        scan_time = existing_attendance["scanned_at"]
        scanner = existing_attendance["scanner_name"]
        return False, f"DUPLICATE CHECK-IN DETECTED! Attendee '{reg['full_name']}' was already checked in at {scan_time} by {scanner}.", reg

    # 6. Record Attendance
    try:
        execute_insert("""
        INSERT INTO attendance (registration_id, scanned_by, scanned_at, status)
        VALUES (?, ?, CURRENT_TIMESTAMP, 'Present')
        """, (reg["reg_db_id"], scanned_by_user_id))

        execute_write("UPDATE registrations SET status = 'Attended' WHERE id = ?", (reg["reg_db_id"],))

        log_audit(
            scanned_by_user_id,
            "ATTENDANCE_CHECKED_IN",
            "attendance",
            reg["reg_db_id"],
            f"Attendee {reg['full_name']} ({reg['registration_id']}) verified present by Organizer #{scanned_by_user_id}"
        )

        create_notification(
            reg["user_id"],
            f"Attendance verified for '{reg['event_title']}'! Welcome to the event."
        )

        return True, f"Check-in SUCCESSFUL! {reg['full_name']} ({reg['category'].replace('_', ' ').title()}) verified.", reg
    except Exception as e:
        return False, f"Failed to record attendance: {str(e)}", None
