# SIMATS Event Sphere

A full-stack university event discovery, registration, payment tracking, attendance verification, and academic credential platform built for **Saveetha Institute of Medical and Technical Sciences (SIMATS Deemed University, Chennai)** using **Python, Streamlit, and SQLite (`simats_events.db`)**.

---

## 🏛️ System Architecture & Highlights

1. **Relational SQLite Engine (`database.py`)**:
   - Normalized relational tables: `users`, `events`, `registrations`, `payments`, `attendance`, `certificates`, `audit_logs`, `notifications`.
   - Foreign key enforcement enabled (`PRAGMA foreign_keys = ON;`).
   - Strict `CHECK` constraints on user roles, event statuses, payment amounts, and unique registration/certificate IDs.
   - Comprehensive initial development seed data covering all user roles and lifecycle statuses.

2. **Authentication & Domain Verification (`auth.py`)**:
   - **Internal Students (`@simats.edu` or `@saveetha.com`)**: Verified automatically upon registration, classified as `internal_verified`, with permanent fee waivers (**₹0.00** locked). Status cannot be altered via profile edits.
   - **External Participants**: Registered with institution affiliation and contact details; can register for free events or pay for paid events.
   - **Organizers**: Provisioned exclusively by Administrators (cannot self-register).
   - **Administrator**: Bootstrapped securely on first run.

3. **Event Lifecycle State Machine (`event_service.py`)**:
   - Explicit workflow: `Draft` $\rightarrow$ `Pending Approval` $\rightarrow$ `Approved` / `Rejected` $\rightarrow$ `Published` $\rightarrow$ `Registration Open` $\rightarrow$ `Registration Closed` / `Full` $\rightarrow$ `Ongoing` $\rightarrow$ `Completed` $\rightarrow$ `Cancelled`.
   - **Material Change Enforcement**: Modifying schedule, venue, format, or fees on an Approved/Published event automatically reverts status to `Pending Approval` for mandatory re-approval!

4. **Mock Payment Simulator (`payment_service.py`)**:
   - Replaces external payment gateways with a clean built-in simulator.
   - Internal students enjoy instant 1-click registration with permanent ₹0.00 fee waiver.
   - External participants on paid events access a simulated payment modal (UPI / Card / Net Banking) featuring explicit **"Simulate Payment Success"** and **"Simulate Payment Failure"** actions.
   - Atomic capacity enforcement and duplicate registration prevention.

5. **Tamper-Evident QR Ticketing & Attendance Scanner (`qr_service.py`)**:
   - Individual QR codes generated for every registration using `qrcode`.
   - Dual-mode check-in station:
     - **Mode A**: Real-time camera scanner (`st.camera_input`) using `opencv-python` to decode QR codes.
     - **Mode B**: Manual Registration ID lookup fallback.
   - Strictly prevents duplicate check-ins, logging timestamps and scanner identity.

6. **Dynamic PDF Certificates & Public Verification (`certificate_service.py`)**:
   - High-quality landscape A4 certificates generated dynamically using `fpdf2`.
   - Locked until the event is marked `Completed` and student attendance is marked `Present`.
   - Embedded verification QR code linking to the public validation registry.
   - Public Certificate Verification page validates authenticity without leaking private contact information.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run app.py
```

---

## 👥 Seed Accounts for Testing & Evaluation

Use the **⚡ 1-Click Demo Accounts Switcher** in the sidebar or login with these credentials:

| Role | Email | Password | Status / Notes |
| :--- | :--- | :--- | :--- |
| **👑 Super Admin** | `admin@simats.edu` | `Admin@123` | Full administrative oversight & approval queue |
| **🏛️ Event Organizer** | `organizer@simats.edu` | `Organizer@123` | Dr. Ramesh Kumar (CSE) - creates & manages events |
| **🏛️ Event Organizer** | `biotech.org@simats.edu` | `Organizer@123` | Dr. Priya Sharma (Biotech) - event organizer |
| **🎓 Internal Student** | `arun.v@simats.edu` | `Student@123` | Verified internal student (**₹0.00 fee waiver**) |
| **🎓 Internal Student** | `divya.s@simats.edu` | `Student@123` | Verified internal student (**₹0.00 fee waiver**) |
| **🌐 External Participant** | `karthik.external@gmail.com` | `External@123` | Anna University participant |
| **🌐 External Participant** | `sneha.p@vit.ac.in` | `External@123` | VIT participant |

---

## 🧪 Automated Test Suite
To run the automated test suite verifying all 7 test suites:
```bash
python test_app.py
```
