# MASTER BUILD SPECIFICATION — SIMATS EVENT SPHERE (Python Streamlit & SQLite Adaptation)

## 1. Project Overview
Build a complete, production-ready, full-stack local web application named **SIMATS Event Sphere** using **Python, Streamlit, and a local SQLite database (`simats_events.db`)**.

SIMATS Event Sphere is a centralized event discovery, registration, management, payment tracking, attendance verification, and certificate distribution platform for SIMATS internal students and external participants.

The application must support three distinct user roles:
1. **Student / Participant** — internal SIMATS students and external participants.
2. **Event Organizer** — authorized users who create and manage events.
3. **Administrator** — authorized users who approve events, manage access, oversee the platform, and maintain accountability.

The application must be fully functional from authentication to execution. All forms, dashboards, filters, buttons, registration workflows, attendance tools, notifications, and certificate actions must be connected to real application logic and persistent database records in SQLite. No mock data substitutes for required functionality (aside from clean development seed data).

---

## 2. Technical Architecture & Overrides
* **Frontend & Backend UI:** Python Streamlit (`streamlit`), utilizing native widgets, clean layout containers, custom CSS injection for professional university styling, and session state management.
* **Database:** SQLite (`sqlite3`) with fully normalized relational tables, foreign keys enabled, check constraints, indexes, and automated migrations/seeding.
* **Authentication:** Secure custom session-based local authentication table managing secure password hashing (`bcrypt` or `hashlib`), roles, and internal domain verification.
* **Payments (Mock Simulator Override):** Completely bypass Razorpay SDKs and external gateways. Replace them with a built-in **Mock Payment Simulator**:
  * Internal verified students (`@simats.edu`) permanently resolve fees to **₹0.00** with instant 1-click registration.
  * External students on paid events see a clean simulated payment modal (Card/UPI input field with "Simulate Success" and "Simulate Failure" buttons) recording transaction IDs and receipts directly to the database.
* **Certificates:** Server-side dynamic PDF generation using `fpdf2` or `reportlab`, locked until event completion and attendance verification.
* **QR Codes:** Standard `qrcode` library for generating secure ticket QR codes, paired with an integrated camera/manual lookup attendance scanner.

---

## 3. Branding and User Interface
* **Aesthetic:** Premium university technology aesthetic with clean layouts, balanced spacing, readable typography, and an academic color palette.
* **Public Landing Page:** Branding, upcoming approved events, featured events, category browsing, search/filtering, sign-in/registration, and platform information. Only approved, published, non-cancelled events appear in public listings.

---

## 4. Authentication and Account Classification
### 4.1 Student Registration & Verification
* Students register with an email address and secure password.
* **Internal Participant Rules:** Email must match a configurable allowlist of domains (default: `@simats.edu`). Successful verification grants `internal_verified` status and permanently fixes registration fees at **₹0.00**. Status cannot be changed via profile edits.
* **External Participant Rules:** Non-matching emails register as `external` participants, collecting full name, organization/institution, and contact details.

### 4.2 Organizer & Administrator Accounts
* **Organizers:** Created or invited exclusively by Administrators. Cannot self-register.
* **Administrators:** Bootstrapped via a secure initialization script or secure default check on first run.
* **Auth Requirements:** Session management, protected routes based on user role stored in `st.session_state`, and server-side authorization checks for every sensitive action.

---

## 5. Dashboards & Event Discovery
* **Internal Student Dashboard:** Greetings, upcoming/recommended events, registrations, QR tickets, payment status (showing ₹0), notifications, certificates, and profile settings.
* **External Participant Dashboard:** Same capabilities plus applicable fees, payment/transaction status, receipts, and institution details.
* **Event Discovery & Filtering:** Search by name, category, date range, venue, eligibility (internal/external), free/paid status, and registration availability. Detailed event view showing agenda, venue, capacity, and pricing.

---

## 6. Event Creation and Management
### 6.1 Event Creation Form
Fields include title, summary, description, banner upload, category, format (in-person/online/hybrid), venue/meeting link, start/end dates/times, registration opening/closing dates, capacity, eligible categories, internal fee (locked at ₹0), external fee, contact details, organizer/department info, agenda, and certificate signatory details.

### 6.2 Event Lifecycle State Machine
Explicit statuses: `Draft`, `Pending Approval`, `Approved`, `Rejected`, `Published`, `Registration Open`, `Registration Closed`, `Full`, `Ongoing`, `Completed`, `Cancelled`.
* Workflow: Draft $\rightarrow$ Pending Approval $\rightarrow$ Administrator Review (Approve/Reject with feedback) $\rightarrow$ Published. Material changes to approved events trigger reapproval requirements.

---

## 7. Administrator & Organizer Dashboards
* **Administrator Dashboard:** System overview metrics (total users, internal/external counts, events, pending approvals, financial totals, fee collections, refunds), Event Approval Queue, User/Organizer Management, and Platform Reports.
* **Organizer Dashboard:** Event metrics, draft/published tracking, registration breakdowns, attendance counts, gross/net collections, participant management tables with filters, CSV export, and attendance review.

---

## 8. Registration, Capacity & QR Attendance
* **Registration Processing:** Atomic capacity checks, duplicate prevention, fee calculation, unique registration ID generation, mock payment processing (or ₹0 confirmation), and QR ticket generation.
* **QR Tickets & Attendance Scanner:** Unique QR codes generated via `qrcode`. Organizer attendance scanner interface using `st.camera_input` / `opencv-python` with a manual Registration ID lookup fallback. Prevents duplicate check-ins and logs actor timestamps.

---

## 9. Certificates & Notifications
* **Certificate Eligibility:** Unlocked *only* when the event is marked `Completed` and attendance is marked `Present`.
* **PDF Generation:** Server-side generation using `fpdf2` containing recipient name, event title, date, unique certificate ID, and QR verification link. Protected against duplicate issuance.
* **Public Verification Page:** Accessible via verification URL/QR code to confirm certificate validity without exposing private data.
* **In-App Notifications:** Notification center tracking registration confirmations, payment results, event approvals, cancellations, and certificate issuance.

---

## 10. Database Schema (`database.py`)
Relational SQLite schema containing tables for:
1. `users` (id, email, password_hash, role, category, institution, created_at)
2. `events` (id, title, summary, description, category, format, venue, start_time, end_time, reg_start, reg_end, capacity, internal_fee, external_fee, status, organizer_id, signatory_details, created_at)
3. `registrations` (id, event_id, user_id, registration_id, status, payment_status, created_at)
4. `payments` (id, registration_id, user_id, amount, currency, transaction_id, status, created_at)
5. `attendance` (id, registration_id, scanned_by, scanned_at, status)
6. `certificates` (id, registration_id, certificate_id, issue_date, status, file_path)
7. `audit_logs` (id, actor_id, action, target_table, target_id, timestamp, details)
8. `notifications` (id, user_id, message, is_read, created_at)