"""
SIMATS Event Sphere - Event Lifecycle & Service Module
Manages event creation, administrative approvals, lifecycle state machine,
material modification tracking, and multi-parameter event discovery.
"""

import datetime
from database import (
    execute_query,
    execute_query_one,
    execute_insert,
    execute_write,
    log_audit,
    create_notification
)

VALID_STATUSES = [
    "Draft",
    "Pending Approval",
    "Approved",
    "Rejected",
    "Published",
    "Registration Open",
    "Registration Closed",
    "Full",
    "Ongoing",
    "Completed",
    "Cancelled"
]

EVENT_CATEGORIES = [
    "Technical",
    "Cultural",
    "Sports",
    "Workshop",
    "Conference",
    "Symposium",
    "Hackathon"
]

EVENT_FORMATS = ["In-Person", "Online", "Hybrid"]


def get_effective_status(event: dict) -> str:
    """
    Computes real-time dynamic registration status based on current timestamp
    and capacity counts without corrupting persistent state.
    """
    persisted_status = event.get("status")
    if persisted_status in ["Draft", "Pending Approval", "Rejected", "Ongoing", "Completed", "Cancelled"]:
        return persisted_status

    # For Approved/Published/Registration Open/Registration Closed/Full:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg_start = event.get("reg_start", "")
    reg_end = event.get("reg_end", "")
    capacity = event.get("capacity", 0)

    # Check capacity
    count_row = execute_query_one(
        "SELECT COUNT(*) as c FROM registrations WHERE event_id = ? AND status != 'Cancelled'",
        (event["id"],)
    )
    reg_count = count_row["c"] if count_row else 0

    if reg_count >= capacity:
        return "Full"

    if now_str < reg_start:
        return "Published"  # Visible, but registration has not started yet
    elif reg_start <= now_str <= reg_end:
        return "Registration Open"
    else:
        return "Registration Closed"


def create_event(
    organizer_id: int,
    title: str,
    summary: str,
    description: str,
    banner_url: str,
    category: str,
    format_type: str,
    venue: str,
    start_time: str,
    end_time: str,
    reg_start: str,
    reg_end: str,
    capacity: int,
    external_fee: float,
    agenda: str = "",
    signatory_name: str = "",
    signatory_title: str = "",
    submit_for_approval: bool = False
) -> tuple[bool, str, int | None]:
    """Create a new event record in Draft or Pending Approval status."""
    if not title or not venue or not start_time or not end_time or not reg_start or not reg_end:
        return False, "Title, venue, event dates, and registration windows are mandatory.", None

    if capacity <= 0:
        return False, "Capacity must be greater than zero.", None

    if external_fee < 0:
        return False, "External fee cannot be negative.", None

    initial_status = "Pending Approval" if submit_for_approval else "Draft"

    sql = """
    INSERT INTO events (
        title, summary, description, banner_url, category, format, venue,
        start_time, end_time, reg_start, reg_end, capacity, internal_fee,
        external_fee, status, organizer_id, admin_feedback, agenda,
        signatory_name, signatory_title, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, NULL, ?, ?, ?, CURRENT_TIMESTAMP)
    """

    try:
        event_id = execute_insert(sql, (
            title.strip(), summary.strip(), description.strip(), banner_url.strip(),
            category, format_type, venue.strip(), start_time, end_time,
            reg_start, reg_end, capacity, external_fee, initial_status,
            organizer_id, agenda.strip(), signatory_name.strip(), signatory_title.strip()
        ))

        action_name = "EVENT_SUBMITTED" if submit_for_approval else "EVENT_DRAFT_CREATED"
        log_audit(organizer_id, action_name, "events", event_id, f"Event '{title}' created with status '{initial_status}'")
        
        # Notify admins if submitted for approval
        if submit_for_approval:
            admins = execute_query("SELECT id FROM users WHERE role = 'admin'")
            for a in admins:
                create_notification(a["id"], f"New event pending approval: '{title}' submitted by Organizer #{organizer_id}.")

        msg = "Event submitted for Administrator approval!" if submit_for_approval else "Event saved as Draft."
        return True, msg, event_id
    except Exception as e:
        return False, f"Failed to create event: {str(e)}", None


def update_event(
    event_id: int,
    actor_id: int,
    actor_role: str,
    title: str,
    summary: str,
    description: str,
    banner_url: str,
    category: str,
    format_type: str,
    venue: str,
    start_time: str,
    end_time: str,
    reg_start: str,
    reg_end: str,
    capacity: int,
    external_fee: float,
    agenda: str = "",
    signatory_name: str = "",
    signatory_title: str = ""
) -> tuple[bool, str]:
    """
    Updates event details.
    Enforces the material change business rule:
    Material changes to approved or published events trigger reapproval requirements!
    """
    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found."

    # Authorization: Only creator organizer or Admin can edit
    if actor_role != "admin" and event["organizer_id"] != actor_id:
        return False, "You do not have permission to edit this event."

    current_status = event["status"]
    is_reapproval_triggered = False
    new_status = current_status

    # Detect material changes on Approved or Published events
    if current_status in ["Approved", "Published", "Registration Open", "Registration Closed", "Full"] and actor_role != "admin":
        material_changed = (
            event["start_time"] != start_time or
            event["end_time"] != end_time or
            event["venue"] != venue or
            event["format"] != format_type or
            float(event["external_fee"]) != float(external_fee) or
            int(capacity) < int(event["capacity"])  # capacity reduction is material
        )
        if material_changed:
            new_status = "Pending Approval"
            is_reapproval_triggered = True

    sql = """
    UPDATE events
    SET title = ?, summary = ?, description = ?, banner_url = ?, category = ?,
        format = ?, venue = ?, start_time = ?, end_time = ?, reg_start = ?,
        reg_end = ?, capacity = ?, external_fee = ?, status = ?,
        agenda = ?, signatory_name = ?, signatory_title = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """

    try:
        execute_write(sql, (
            title.strip(), summary.strip(), description.strip(), banner_url.strip(),
            category, format_type, venue.strip(), start_time, end_time,
            reg_start, reg_end, capacity, external_fee, new_status,
            agenda.strip(), signatory_name.strip(), signatory_title.strip(), event_id
        ))

        if is_reapproval_triggered:
            log_audit(actor_id, "EVENT_MATERIAL_CHANGE", "events", event_id, f"Material edits caused event '{title}' to revert to 'Pending Approval'")
            # Notify admins
            admins = execute_query("SELECT id FROM users WHERE role = 'admin'")
            for a in admins:
                create_notification(a["id"], f"Event '{title}' underwent material changes by organizer and requires re-approval.")
            return True, "Event updated. Due to material changes (schedule/venue/fee), the event has been reverted to 'Pending Approval' for Administrator review."
        else:
            log_audit(actor_id, "EVENT_UPDATED", "events", event_id, f"Event '{title}' updated.")
            return True, "Event updated successfully."
    except Exception as e:
        return False, f"Failed to update event: {str(e)}"


def submit_draft_for_approval(event_id: int, organizer_id: int) -> tuple[bool, str]:
    """Transition Draft or Rejected event to Pending Approval."""
    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found."
    if event["organizer_id"] != organizer_id:
        return False, "Unauthorized."
    if event["status"] not in ["Draft", "Rejected"]:
        return False, f"Cannot submit event with status '{event['status']}' for approval."

    execute_write("UPDATE events SET status = 'Pending Approval', admin_feedback = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (event_id,))
    log_audit(organizer_id, "EVENT_SUBMITTED_APPROVAL", "events", event_id, f"Event '{event['title']}' submitted for approval.")
    
    admins = execute_query("SELECT id FROM users WHERE role = 'admin'")
    for a in admins:
        create_notification(a["id"], f"Organizer submitted '{event['title']}' for review.")
    return True, "Event submitted for approval."


def admin_review_event(admin_id: int, event_id: int, decision: str, feedback: str = "") -> tuple[bool, str]:
    """
    Administrator reviews pending event:
    decision: 'Approve' -> 'Approved'
    decision: 'Reject' -> 'Rejected' (requires feedback)
    """
    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found."
    if event["status"] != "Pending Approval":
        return False, f"Event is not in 'Pending Approval' status (currently '{event['status']}')."

    if decision == "Approve":
        execute_write("""
        UPDATE events
        SET status = 'Approved', admin_feedback = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (feedback or "Approved by Administrator", event_id))
        log_audit(admin_id, "EVENT_APPROVED", "events", event_id, f"Admin #{admin_id} approved event '{event['title']}'")
        create_notification(event["organizer_id"], f"Your event '{event['title']}' has been APPROVED! You may now publish it to the platform.")
        return True, "Event approved successfully."
    elif decision == "Reject":
        if not feedback.strip():
            return False, "Rejection requires actionable feedback for the organizer."
        execute_write("""
        UPDATE events
        SET status = 'Rejected', admin_feedback = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (feedback.strip(), event_id))
        log_audit(admin_id, "EVENT_REJECTED", "events", event_id, f"Admin #{admin_id} rejected event '{event['title']}'. Feedback: {feedback}")
        create_notification(event["organizer_id"], f"Your event '{event['title']}' was REJECTED by Admin. Feedback: {feedback}")
        return True, "Event rejected with feedback."
    else:
        return False, "Invalid decision."


def publish_event(actor_id: int, event_id: int) -> tuple[bool, str]:
    """Publish an approved event so it becomes publicly visible and open for registrations."""
    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found."
    if event["status"] not in ["Approved", "Registration Closed"]:
        return False, f"Only 'Approved' events can be published (current: {event['status']})."

    execute_write("UPDATE events SET status = 'Published', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (event_id,))
    log_audit(actor_id, "EVENT_PUBLISHED", "events", event_id, f"Event '{event['title']}' published.")
    create_notification(event["organizer_id"], f"Event '{event['title']}' is now live on SIMATS Event Sphere!")
    return True, "Event published to the public landing page!"


def set_event_status(actor_id: int, event_id: int, new_status: str) -> tuple[bool, str]:
    """
    Transition event through operational statuses:
    'Ongoing', 'Completed', 'Cancelled'.
    """
    if new_status not in VALID_STATUSES:
        return False, "Invalid target status."

    event = execute_query_one("SELECT * FROM events WHERE id = ?", (event_id,))
    if not event:
        return False, "Event not found."

    execute_write("UPDATE events SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, event_id))
    log_audit(actor_id, "EVENT_STATUS_CHANGED", "events", event_id, f"Event status transitioned from '{event['status']}' to '{new_status}'")

    # If cancelled, notify all registered participants
    if new_status == "Cancelled":
        registrants = execute_query("SELECT user_id FROM registrations WHERE event_id = ? AND status != 'Cancelled'", (event_id,))
        for r in registrants:
            create_notification(r["user_id"], f"IMPORTANT: Event '{event['title']}' has been CANCELLED. Any paid fees will be refunded.")

    # If completed, notify registrants that certificates may be eligible
    if new_status == "Completed":
        registrants = execute_query("SELECT user_id FROM registrations WHERE event_id = ? AND status = 'Attended'", (event_id,))
        for r in registrants:
            create_notification(r["user_id"], f"Event '{event['title']}' has concluded! Your certificate is now unlocked for download in your dashboard.")

    return True, f"Event status updated to '{new_status}'."


def get_public_events(
    search: str = "",
    category: str = "All",
    format_type: str = "All",
    fee_filter: str = "All",
    date_filter: str = "All"
) -> list[dict]:
    """
    Query events visible on the public landing page.
    Only approved, published, ongoing, or completed events are shown.
    Drafts and rejected events are NEVER visible publicly.
    """
    sql = """
    SELECT e.*, u.full_name as organizer_name, u.email as organizer_email,
           (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status != 'Cancelled') as registered_count
    FROM events e
    JOIN users u ON e.organizer_id = u.id
    WHERE e.status IN ('Approved', 'Published', 'Registration Open', 'Registration Closed', 'Full', 'Ongoing', 'Completed')
    """
    params = []

    if search.strip():
        sql += " AND (e.title LIKE ? OR e.summary LIKE ? OR e.venue LIKE ? OR e.description LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term, term])

    if category != "All":
        sql += " AND e.category = ?"
        params.append(category)

    if format_type != "All":
        sql += " AND e.format = ?"
        params.append(format_type)

    if fee_filter == "Free (₹0)":
        sql += " AND e.external_fee = 0.0"
    elif fee_filter == "Paid (External)":
        sql += " AND e.external_fee > 0.0"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if date_filter == "Upcoming":
        sql += " AND e.end_time >= ?"
        params.append(now_str)
    elif date_filter == "Past Events":
        sql += " AND e.end_time < ?"
        params.append(now_str)

    sql += " ORDER BY e.start_time ASC"
    rows = execute_query(sql, tuple(params))
    
    # Attach effective status
    for row in rows:
        row["effective_status"] = get_effective_status(row)

    return rows


def get_event_by_id(event_id: int) -> dict | None:
    """Fetch complete event details with organizer metadata and registration statistics."""
    sql = """
    SELECT e.*, u.full_name as organizer_name, u.email as organizer_email, u.institution as organizer_institution,
           (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status != 'Cancelled') as registered_count,
           (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'Attended') as attended_count
    FROM events e
    JOIN users u ON e.organizer_id = u.id
    WHERE e.id = ?
    """
    event = execute_query_one(sql, (event_id,))
    if event:
        event["effective_status"] = get_effective_status(event)
    return event
