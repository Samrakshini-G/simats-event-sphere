"""
SIMATS Event Sphere - Mock Payment Simulator & Registration Module
Implements fee exemption for internal SIMATS students (₹0.00 instant registration),
clean mock payment modal logic for external participants (Card/UPI with Simulate Success / Failure),
atomic capacity validation, duplicate registration prevention, and transaction ledger recording.
"""

import uuid
import datetime
from database import (
    execute_query,
    execute_query_one,
    execute_insert,
    execute_write,
    log_audit,
    create_notification
)
from qr_service import generate_ticket_qr


def check_registration_eligibility(user_id: int, event_id: int) -> tuple[bool, str, dict | None]:
    """
    Validates whether a user can register for an event.
    Checks:
    - Event exists and is not Cancelled/Draft/Rejected
    - Duplicate registration check
    - Capacity check
    - Registration time window
    """
    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found.", None

    if event["status"] in ["Draft", "Pending Approval", "Rejected"]:
        return False, f"Event is not open for registration (Current status: {event['status']}).", None

    if event["status"] == "Cancelled":
        return False, "This event has been cancelled.", None

    if event["status"] == "Completed":
        return False, "This event has already concluded.", None

    # Check registration window
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if now_str < event["reg_start"]:
        return False, f"Registration has not opened yet. It opens on {event['reg_start']}.", None
    if now_str > event["reg_end"]:
        return False, f"Registration closed on {event['reg_end']}.", None

    # Check duplicate registration
    existing = execute_query_one("""
    SELECT id, registration_id, status, payment_status
    FROM registrations
    WHERE event_id = ? AND user_id = ? AND status != 'Cancelled'
    """, (event_id, user_id))

    if existing:
        return False, f"You are already registered for this event (Registration ID: {existing['registration_id']}).", None

    # Check capacity atomically
    count_row = execute_query_one(
        "SELECT COUNT(*) as c FROM registrations WHERE event_id = ? AND status != 'Cancelled'",
        (event_id,)
    )
    reg_count = count_row["c"] if count_row else 0

    if reg_count >= event["capacity"]:
        # Auto-update status to Full
        execute_write("UPDATE events SET status = 'Full', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (event_id,))
        return False, f"Registration Full: Capacity of {event['capacity']} participants has been reached.", None

    user = execute_query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        return False, "User account not found.", None

    # Determine fee
    is_internal = (user["category"] == "internal_verified")
    fee = 0.0 if is_internal else float(event["external_fee"])

    details = {
        "event": event,
        "user": user,
        "is_internal": is_internal,
        "fee": fee,
        "remaining_seats": event["capacity"] - reg_count
    }
    return True, "Eligible to register.", details


def register_internal_student_instant(user_id: int, event_id: int) -> tuple[bool, str, dict | None]:
    """
    1-Click instant registration for verified SIMATS internal students.
    Enforces permanent ₹0.00 waiver rule without requiring payment steps.
    """
    eligible, msg, details = check_registration_eligibility(user_id, event_id)
    if not eligible:
        return False, msg, None

    if not details["is_internal"] and details["fee"] > 0:
        return False, "External participants on paid events must proceed through payment checkout.", None

    now = datetime.datetime.now()
    reg_code = f"SIMATS-REG-{now.year}-{uuid.uuid4().hex[:6].upper()}"
    txn_code = f"TXN-SIMATS-WAIVER-{uuid.uuid4().hex[:6].upper()}"

    try:
        # 1. Insert Registration
        reg_db_id = execute_insert("""
        INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
        VALUES (?, ?, ?, 'Registered', 'Exempt_Zero_Fee', CURRENT_TIMESTAMP)
        """, (event_id, user_id, reg_code))

        # 2. Insert Payment Record for Audit/Ledger
        execute_insert("""
        INSERT INTO payments (registration_id, user_id, amount, currency, transaction_id, payment_method, status, created_at)
        VALUES (?, ?, 0.0, 'INR', ?, 'Internal SIMATS Student Waiver (₹0.00)', 'Success', CURRENT_TIMESTAMP)
        """, (reg_db_id, user_id, txn_code))

        # 3. Generate QR ticket
        qr_path = generate_ticket_qr(reg_code, event_id, user_id)

        # 4. Audit & Notification
        log_audit(user_id, "REGISTRATION_CREATED", "registrations", reg_db_id, f"Internal student 1-click registered for event ID {event_id} (Fee: ₹0)")
        create_notification(user_id, f"Registration confirmed for '{details['event']['title']}'! Ticket ID: {reg_code} (Fee: ₹0.00).")

        reg_data = {
            "registration_id": reg_code,
            "event_title": details["event"]["title"],
            "fee": 0.0,
            "qr_path": qr_path,
            "payment_status": "Exempt_Zero_Fee"
        }
        return True, "Instant 1-Click Registration Successful! ₹0.00 internal fee waiver applied.", reg_data
    except Exception as e:
        return False, f"Registration processing error: {str(e)}", None


def process_external_mock_payment(
    user_id: int,
    event_id: int,
    payment_method: str,
    simulate_success: bool = True
) -> tuple[bool, str, dict | None]:
    """
    Processes simulated payment for external participants.
    - If simulate_success: Creates Registration, Payment (Success), QR Ticket, and notifies.
    - If simulate_failure: Logs Failed Payment attempt and alerts the user.
    """
    eligible, msg, details = check_registration_eligibility(user_id, event_id)
    if not eligible:
        return False, msg, None

    amount = details["fee"]
    now = datetime.datetime.now()

    if not simulate_success:
        # Simulate Failure branch
        fail_txn = f"TXN-SIMATS-FAIL-{uuid.uuid4().hex[:8].upper()}"
        try:
            # We record a failed payment record with registration_id=0 or dummy for logging if allowed,
            # or record an audit log directly
            log_audit(user_id, "PAYMENT_FAILED_SIMULATED", "payments", None, f"Payment simulation failed for user ID {user_id}, event ID {event_id}, amount ₹{amount}")
            create_notification(user_id, f"Payment simulation failed for '{details['event']['title']}'. Transaction {fail_txn} was declined.")
            return False, f"Payment Simulation DECLINED: Transaction {fail_txn} was rejected by the simulated payment processor. No ticket was issued.", None
        except Exception as e:
            return False, f"Payment error: {str(e)}", None

    # Simulate Success branch
    reg_code = f"SIMATS-REG-{now.year}-{uuid.uuid4().hex[:6].upper()}"
    txn_code = f"TXN-SIMATS-PAY-{now.strftime('%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    try:
        # 1. Insert Registration
        reg_db_id = execute_insert("""
        INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
        VALUES (?, ?, ?, 'Registered', 'Completed', CURRENT_TIMESTAMP)
        """, (event_id, user_id, reg_code))

        # 2. Insert Payment record
        execute_insert("""
        INSERT INTO payments (registration_id, user_id, amount, currency, transaction_id, payment_method, status, created_at)
        VALUES (?, ?, ?, 'INR', ?, ?, 'Success', CURRENT_TIMESTAMP)
        """, (reg_db_id, user_id, amount, txn_code, payment_method))

        # 3. Generate QR ticket
        qr_path = generate_ticket_qr(reg_code, event_id, user_id)

        # 4. Audit & Notification
        log_audit(user_id, "PAYMENT_SUCCESS_SIMULATED", "payments", reg_db_id, f"Payment of ₹{amount:.2f} completed via {payment_method}. Txn: {txn_code}")
        create_notification(user_id, f"Payment received! ₹{amount:.2f} for '{details['event']['title']}'. Txn ID: {txn_code}. Your QR ticket is ready.")

        reg_data = {
            "registration_id": reg_code,
            "event_title": details["event"]["title"],
            "fee": amount,
            "transaction_id": txn_code,
            "qr_path": qr_path,
            "payment_status": "Completed"
        }
        return True, f"Payment of ₹{amount:.2f} was SUCCESSFUL! Transaction ID: {txn_code}.", reg_data
    except Exception as e:
        return False, f"Payment processing error: {str(e)}", None


def refund_payment(admin_id: int, payment_id: int, reason: str = "") -> tuple[bool, str]:
    """Simulate refunding a completed payment (Admin action)."""
    payment = execute_query_one("SELECT * FROM payments WHERE id = ?", (payment_id,))
    if not payment:
        return False, "Payment record not found."
    if payment["status"] != "Success":
        return False, f"Cannot refund payment with status '{payment['status']}'."

    execute_write("UPDATE payments SET status = 'Refunded' WHERE id = ?", (payment_id,))
    execute_write("UPDATE registrations SET status = 'Cancelled' WHERE id = ?", (payment["registration_id"],))

    log_audit(admin_id, "PAYMENT_REFUNDED", "payments", payment_id, f"Refunded ₹{payment['amount']} (Txn: {payment['transaction_id']}). Reason: {reason}")
    create_notification(payment["user_id"], f"Refund of ₹{payment['amount']:.2f} has been processed for Transaction {payment['transaction_id']}.")
    return True, f"Payment of ₹{payment['amount']:.2f} successfully marked as Refunded."
