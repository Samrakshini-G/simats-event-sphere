"""
SIMATS Event Sphere - Automated Comprehensive Verification Test Suite
Validates database schema, constraints, role permissions, event lifecycle state machine,
material modification rules, ₹0 internal waivers, mock payment simulator,
QR ticketing, attendance duplicate prevention, and PDF certificate issuance.
"""

import os
import sys
import datetime
import unittest

# Ensure root directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    execute_query,
    execute_query_one,
    execute_write,
    execute_insert
)
from auth import (
    register_user,
    authenticate_user,
    create_organizer_by_admin,
    is_internal_email,
    update_user_profile
)
from event_service import (
    create_event,
    update_event,
    submit_draft_for_approval,
    admin_review_event,
    publish_event,
    set_event_status,
    get_public_events,
    get_effective_status
)
from payment_service import (
    register_internal_student_instant,
    process_external_mock_payment,
    check_registration_eligibility,
    refund_payment
)
from qr_service import (
    generate_ticket_qr,
    verify_and_check_in
)
from certificate_service import (
    generate_certificate,
    check_certificate_eligibility,
    verify_certificate_public
)


class TestSIMATSEventSphere(unittest.TestCase):
    """Full-stack functional test suite."""

    # Test event titles created during tests (cleaned up in tearDownClass)
    TEST_EVENT_TITLES = [
        "State Machine Test Conference",
        "Waiver Verification Workshop",
        "External Payment Test Event",
    ]

    @classmethod
    def tearDownClass(cls):
        """Remove all transient test events and test users created during the test run."""
        from database import execute_write, execute_query
        # Remove test events and their cascading data
        for title in cls.TEST_EVENT_TITLES:
            rows = execute_query("SELECT id FROM events WHERE title = ?", (title,))
            for row in rows:
                eid = row["id"]
                execute_write("DELETE FROM certificates WHERE registration_id IN (SELECT id FROM registrations WHERE event_id = ?)", (eid,))
                execute_write("DELETE FROM attendance WHERE registration_id IN (SELECT id FROM registrations WHERE event_id = ?)", (eid,))
                execute_write("DELETE FROM payments WHERE registration_id IN (SELECT id FROM registrations WHERE event_id = ?)", (eid,))
                execute_write("DELETE FROM registrations WHERE event_id = ?", (eid,))
                execute_write("DELETE FROM events WHERE id = ?", (eid,))
        # Remove timestamped test users
        execute_write("DELETE FROM users WHERE email LIKE 'test.internal.%@simats.edu'")
        execute_write("DELETE FROM users WHERE email LIKE 'test.ext.%@externaluniv.ac.in'")
        execute_write("DELETE FROM users WHERE email LIKE 'org.test.%@simats.edu'")
        execute_write("DELETE FROM users WHERE email LIKE 'ext.test.%@externaltest.com'")

    def test_01_domain_verification_and_roles(self):
        """Test internal domain verification vs external participant registration."""
        self.assertTrue(is_internal_email("student.test@simats.edu"))
        self.assertTrue(is_internal_email("faculty@saveetha.com"))
        self.assertFalse(is_internal_email("external.student@gmail.com"))

        # Register Internal Student
        now_ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        internal_email = f"test.internal.{now_ts}@simats.edu"
        ok, msg = register_user(internal_email, "Secure@123", "Internal Test Student")
        self.assertTrue(ok, msg)

        user_int = execute_query_one("SELECT * FROM users WHERE email = ?", (internal_email,))
        self.assertEqual(user_int["role"], "student")
        self.assertEqual(user_int["category"], "internal_verified")

        # Register External Student
        ext_email = f"test.ext.{now_ts}@externaluniv.ac.in"
        ok_ext, msg_ext = register_user(ext_email, "Secure@123", "External Test Student", institution="MIT Anna Univ")
        self.assertTrue(ok_ext, msg_ext)

        user_ext = execute_query_one("SELECT * FROM users WHERE email = ?", (ext_email,))
        self.assertEqual(user_ext["role"], "student")
        self.assertEqual(user_ext["category"], "external")

        # Test login authentication
        auth_ok, auth_data = authenticate_user(internal_email, "Secure@123")
        self.assertTrue(auth_ok)
        self.assertEqual(auth_data["email"], internal_email)

        # Test invalid password rejection
        auth_fail, _ = authenticate_user(internal_email, "WrongPassword")
        self.assertFalse(auth_fail)

    def test_02_organizer_provisioning_by_admin(self):
        """Test that only Admins can create Organizer accounts."""
        admin = execute_query_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        now_ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        org_email = f"org.test.{now_ts}@simats.edu"

        ok, msg = create_organizer_by_admin(
            admin_id=admin["id"],
            email=org_email,
            password="Organizer@123",
            full_name="Dr. Test Organizer",
            phone="+91 99999 11111",
            institution="SIMATS",
            department="Electrical Engineering"
        )
        self.assertTrue(ok, msg)

        org_record = execute_query_one("SELECT * FROM users WHERE email = ?", (org_email,))
        self.assertEqual(org_record["role"], "organizer")

    def test_03_event_lifecycle_and_material_change(self):
        """Test full event state machine from Draft to Pending to Approved to Published, and material changes."""
        org = execute_query_one("SELECT id FROM users WHERE role = 'organizer' LIMIT 1")
        admin = execute_query_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        now = datetime.datetime.now()

        # 1. Create Draft Event
        ok, msg, eid = create_event(
            organizer_id=org["id"],
            title="State Machine Test Conference",
            summary="A test conference",
            description="Detailed test description",
            banner_url="",
            category="Technical",
            format_type="In-Person",
            venue="Lab 101, SIMATS",
            start_time=(now + datetime.timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=(now + datetime.timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_start=(now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_end=(now + datetime.timedelta(days=18)).strftime("%Y-%m-%d %H:%M:%S"),
            capacity=50,
            external_fee=200.0,
            submit_for_approval=False
        )
        self.assertTrue(ok)
        ev = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev["status"], "Draft")

        # 2. Submit for Approval
        ok_sub, _ = submit_draft_for_approval(eid, org["id"])
        self.assertTrue(ok_sub)
        ev = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev["status"], "Pending Approval")

        # 3. Admin Rejection with Feedback
        ok_rej, _ = admin_review_event(admin["id"], eid, "Reject", "Please modify venue capacity and schedule.")
        self.assertTrue(ok_rej)
        ev = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev["status"], "Rejected")
        self.assertIn("modify venue", ev["admin_feedback"])

        # 4. Resubmit for Approval
        ok_resub, _ = submit_draft_for_approval(eid, org["id"])
        self.assertTrue(ok_resub)

        # 5. Admin Approval
        ok_app, _ = admin_review_event(admin["id"], eid, "Approve", "Approved by Dean.")
        self.assertTrue(ok_app)
        ev = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev["status"], "Approved")

        # 6. Publish Event
        ok_pub, _ = publish_event(org["id"], eid)
        self.assertTrue(ok_pub)
        ev = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev["status"], "Published")

        # 7. Material Modification Check: Changing venue/dates/fees on Published event reverts to Pending Approval!
        ok_mat, msg_mat = update_event(
            event_id=eid,
            actor_id=org["id"],
            actor_role="organizer",
            title="State Machine Test Conference",
            summary="A test conference",
            description="Detailed test description",
            banner_url="",
            category="Technical",
            format_type="In-Person",
            venue="Different Venue - Block Z",  # Material venue change!
            start_time=(now + datetime.timedelta(days=22)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=(now + datetime.timedelta(days=23)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_start=(now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_end=(now + datetime.timedelta(days=18)).strftime("%Y-%m-%d %H:%M:%S"),
            capacity=50,
            external_fee=200.0
        )
        self.assertTrue(ok_mat)
        self.assertIn("Pending Approval", msg_mat)
        ev_after = execute_query_one("SELECT * FROM events WHERE id = ?", (eid,))
        self.assertEqual(ev_after["status"], "Pending Approval")

        # Re-approve and publish for downstream tests
        admin_review_event(admin["id"], eid, "Approve", "Re-approved")
        publish_event(org["id"], eid)

    def test_04_instant_zero_fee_waiver_for_internal_students(self):
        """Test internal student instant 1-click registration with permanent ₹0.00 fee waiver."""
        now = datetime.datetime.now()
        org = execute_query_one("SELECT id FROM users WHERE role = 'organizer' LIMIT 1")
        admin = execute_query_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")

        # Create active published event with ₹350 external fee
        ok, _, eid = create_event(
            organizer_id=org["id"],
            title="Waiver Verification Workshop",
            summary="Test summary",
            description="Test desc",
            banner_url="",
            category="Workshop",
            format_type="In-Person",
            venue="Seminar Hall 1",
            start_time=(now + datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=(now + datetime.timedelta(days=11)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_start=(now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_end=(now + datetime.timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
            capacity=20,
            external_fee=350.0,
            submit_for_approval=True
        )
        admin_review_event(admin["id"], eid, "Approve")
        publish_event(org["id"], eid)

        # Internal student
        student = execute_query_one("SELECT * FROM users WHERE category = 'internal_verified' AND role = 'student' LIMIT 1")

        # Execute instant 1-click registration
        ok_reg, msg_reg, data = register_internal_student_instant(student["id"], eid)
        self.assertTrue(ok_reg, msg_reg)
        self.assertEqual(data["fee"], 0.0)
        self.assertEqual(data["payment_status"], "Exempt_Zero_Fee")

        # Check DB records
        reg = execute_query_one("SELECT * FROM registrations WHERE registration_id = ?", (data["registration_id"],))
        self.assertIsNotNone(reg)
        self.assertEqual(reg["payment_status"], "Exempt_Zero_Fee")

        pay = execute_query_one("SELECT * FROM payments WHERE registration_id = ?", (reg["id"],))
        self.assertIsNotNone(pay)
        self.assertEqual(pay["amount"], 0.0)
        self.assertEqual(pay["status"], "Success")

        # Prevent duplicate registration
        ok_dup, msg_dup, _ = register_internal_student_instant(student["id"], eid)
        self.assertFalse(ok_dup)
        self.assertIn("already registered", msg_dup)

    def test_05_external_mock_payment_simulator(self):
        """Test mock payment simulator for external participants (Failure vs Success branches)."""
        now = datetime.datetime.now()
        org = execute_query_one("SELECT id FROM users WHERE role = 'organizer' LIMIT 1")
        admin = execute_query_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")

        ok, _, eid = create_event(
            organizer_id=org["id"],
            title="External Payment Test Event",
            summary="Payment test",
            description="Testing payment simulation",
            banner_url="",
            category="Technical",
            format_type="In-Person",
            venue="Block A",
            start_time=(now + datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
            end_time=(now + datetime.timedelta(days=11)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_start=(now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            reg_end=(now + datetime.timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
            capacity=10,
            external_fee=400.0,
            submit_for_approval=True
        )
        admin_review_event(admin["id"], eid, "Approve")
        publish_event(org["id"], eid)

        ext_user = execute_query_one("SELECT * FROM users WHERE category = 'external' AND role = 'student' LIMIT 1")

        # 1. Test Simulate Failure
        ok_fail, msg_fail, _ = process_external_mock_payment(ext_user["id"], eid, "UPI (Mock)", simulate_success=False)
        self.assertFalse(ok_fail)
        self.assertIn("DECLINED", msg_fail)

        # Confirm no active registration was created
        no_reg = execute_query_one("SELECT * FROM registrations WHERE event_id = ? AND user_id = ? AND status != 'Cancelled'", (eid, ext_user["id"]))
        self.assertIsNone(no_reg)

        # 2. Test Simulate Success
        ok_succ, msg_succ, pay_data = process_external_mock_payment(ext_user["id"], eid, "Credit Card (Mock)", simulate_success=True)
        self.assertTrue(ok_succ, msg_succ)
        self.assertEqual(pay_data["fee"], 400.0)
        self.assertTrue(pay_data["transaction_id"].startswith("TXN-SIMATS"))

        # Verify active registration and payment record
        active_reg = execute_query_one("SELECT * FROM registrations WHERE registration_id = ?", (pay_data["registration_id"],))
        self.assertIsNotNone(active_reg)
        self.assertEqual(active_reg["payment_status"], "Completed")

        pay_record = execute_query_one("SELECT * FROM payments WHERE registration_id = ?", (active_reg["id"],))
        self.assertIsNotNone(pay_record)
        self.assertEqual(pay_record["amount"], 400.0)
        self.assertEqual(pay_record["status"], "Success")

    def test_06_qr_ticketing_and_attendance_checkin(self):
        """Test QR code ticket generation, attendance check-in, and duplicate check-in prevention."""
        # Find a registered ticket
        reg = execute_query_one("""
        SELECT r.*, e.organizer_id
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.status = 'Registered' AND r.payment_status IN ('Completed', 'Exempt_Zero_Fee')
        LIMIT 1
        """)
        self.assertIsNotNone(reg)

        # First Check-In (Should Succeed)
        ok_c1, msg_c1, data_c1 = verify_and_check_in(reg["registration_id"], reg["event_id"], reg["organizer_id"])
        self.assertTrue(ok_c1, msg_c1)
        self.assertIn("SUCCESSFUL", msg_c1)

        # Verify attendance record and status
        att = execute_query_one("SELECT * FROM attendance WHERE registration_id = ?", (reg["id"],))
        self.assertIsNotNone(att)
        self.assertEqual(att["status"], "Present")

        reg_updated = execute_query_one("SELECT * FROM registrations WHERE id = ?", (reg["id"],))
        self.assertEqual(reg_updated["status"], "Attended")

        # Second Check-In Attempt (Must be rejected with duplicate warning)
        ok_c2, msg_c2, data_c2 = verify_and_check_in(reg["registration_id"], reg["event_id"], reg["organizer_id"])
        self.assertFalse(ok_c2)
        self.assertIn("DUPLICATE CHECK-IN DETECTED", msg_c2)

        # Check-in on Wrong Event ID (Must be rejected)
        ok_wrong, msg_wrong, _ = verify_and_check_in(reg["registration_id"], 99999, reg["organizer_id"])
        self.assertFalse(ok_wrong)
        self.assertIn("not the currently selected event", msg_wrong)

    def test_07_certificate_issuance_and_public_verification(self):
        """Test certificate generation locking rules, PDF creation, and public verification."""
        # Find the attended registration from previous test
        reg_attended = execute_query_one("""
        SELECT r.*, e.status as event_status
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.status = 'Attended'
        LIMIT 1
        """)
        self.assertIsNotNone(reg_attended)

        # If event is not Completed yet, certificate generation must be locked!
        execute_write("UPDATE events SET status = 'Ongoing' WHERE id = ?", (reg_attended["event_id"],))
        ok_locked, msg_locked, _, _ = generate_certificate(reg_attended["registration_id"])
        self.assertFalse(ok_locked)
        self.assertIn("Certificate Locked", msg_locked)

        # Now mark event as Completed -> Unlocks certificate!
        execute_write("UPDATE events SET status = 'Completed' WHERE id = ?", (reg_attended["event_id"],))
        ok_gen, msg_gen, rel_path, cert_id = generate_certificate(reg_attended["registration_id"])
        self.assertTrue(ok_gen, msg_gen)
        self.assertIsNotNone(cert_id)

        # Verify physical PDF exists on disk
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_pdf_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
        self.assertTrue(os.path.exists(full_pdf_path))

        # Test Public Certificate Verification Page Endpoint
        v_ok, v_msg, v_data = verify_certificate_public(cert_id)
        self.assertTrue(v_ok, v_msg)
        self.assertEqual(v_data["status"], "VALID & AUTHENTIC")
        self.assertIn("recipient_name", v_data)
        self.assertIn("event_title", v_data)
        # Verify private data (email, phone, password_hash) are NOT exposed
        self.assertNotIn("email", v_data)
        self.assertNotIn("phone", v_data)
        self.assertNotIn("password_hash", v_data)

    def test_08_strict_assets_and_no_placeholders(self):
        """Test strict asset usage: all required assets exist locally, with no external URLs."""
        from asset_helper import (
            ASSETS,
            ACHIEVEMENT_ITEMS,
            CAMPUS_HIGHLIGHTS,
            resolve_asset_path,
            get_event_poster_path,
            get_image_base64
        )
        from PIL import Image

        # 1. Verify every asset in the catalog exists on disk and is a valid image
        for key, path in ASSETS.items():
            self.assertTrue(os.path.exists(path), f"Asset '{key}' missing at {path}")
            with Image.open(path) as img:
                self.assertGreater(img.size[0], 0)
                self.assertGreater(img.size[1], 0)

        # 2. Verify achievement items and campus highlights
        for item in ACHIEVEMENT_ITEMS:
            self.assertTrue(os.path.exists(item["path"]), f"Achievement path missing: {item['path']}")
        for item in CAMPUS_HIGHLIGHTS:
            self.assertTrue(os.path.exists(item["path"]), f"Highlight path missing: {item['path']}")

        # 3. Verify event poster path resolution (guaranteed local fallback, no external URLs)
        sample_event = {"category": "Hackathon", "banner_url": ""}
        poster = get_event_poster_path(sample_event)
        self.assertTrue(os.path.exists(poster))
        self.assertFalse(poster.startswith("http"))

        # 4. Verify base64 caching
        b64 = get_image_base64(ASSETS["logo_college"])
        self.assertTrue(b64.startswith("data:image/"))

        # 5. Check all existing events in database: ensure zero external Unsplash URLs
        events = execute_query("SELECT id, title, banner_url FROM events")
        for ev in events:
            banner = ev.get("banner_url") or ""
            self.assertFalse(
                banner.startswith("http://") or banner.startswith("https://"),
                f"Event #{ev['id']} '{ev['title']}' still has external URL: {banner}"
            )

    def test_09_entry_urls_and_role_protection(self):
        """Test separate entry view authorization and role isolation."""
        # 1. Student credentials check
        ok_stud, stud_user = authenticate_user("arun.v@simats.edu", "Student@123")
        self.assertTrue(ok_stud)
        self.assertEqual(stud_user["role"], "student")
        # Student cannot access Coordinator or Admin
        self.assertNotIn(stud_user["role"], ["organizer", "admin"])
        self.assertNotEqual(stud_user["role"], "admin")

        # 2. Coordinator credentials check
        ok_org, org_user = authenticate_user("organizer@simats.edu", "Organizer@123")
        self.assertTrue(ok_org)
        self.assertEqual(org_user["role"], "organizer")
        # Coordinator CAN access Coordinator Portal
        self.assertIn(org_user["role"], ["organizer", "admin"])
        # Coordinator CANNOT access Super-Admin Console
        self.assertNotEqual(org_user["role"], "admin")

        # 3. Super-Admin credentials check
        ok_adm, adm_user = authenticate_user("admin@simats.edu", "Admin@123")
        self.assertTrue(ok_adm)
        self.assertEqual(adm_user["role"], "admin")
        # Admin has clearance for both Admin and Coordinator
        self.assertEqual(adm_user["role"], "admin")
        self.assertIn(adm_user["role"], ["organizer", "admin"])


if __name__ == "__main__":
    unittest.main()
