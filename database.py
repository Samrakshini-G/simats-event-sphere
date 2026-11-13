"""
SIMATS Event Sphere - Database Architecture & Relational Schema (SQLite)
Implements normalized relational tables, foreign keys, check constraints,
indexes, transaction helpers, and complete initial development seed data.
"""

import os
import sqlite3
import datetime
from contextlib import contextmanager
import bcrypt

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "simats_events.db")
STATIC_DIR = os.path.join(DB_DIR, "static")
QR_DIR = os.path.join(STATIC_DIR, "qrcodes")
CERT_DIR = os.path.join(STATIC_DIR, "certificates")
AVATARS_DIR = os.path.join(STATIC_DIR, "avatars")
POSTERS_DIR = os.path.join(STATIC_DIR, "posters")

# Ensure required storage directories exist
os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(POSTERS_DIR, exist_ok=True)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


@contextmanager
def get_db():
    """
    Context manager for SQLite database connection.
    Enforces foreign keys and returns rows as sqlite3.Row objects.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(sql: str, params: tuple = ()) -> list:
    """Execute a read query and return all results as dicts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_query_one(sql: str, params: tuple = ()) -> dict | None:
    """Execute a read query and return a single result dict or None."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute_insert(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT statement and return the last row id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid


def execute_write(sql: str, params: tuple = ()) -> int:
    """Execute an UPDATE or DELETE statement and return affected rows count."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount


def log_audit(actor_id: int | None, action: str, target_table: str, target_id: int | None, details: str = ""):
    """Helper to record an audit log entry for system accountability."""
    sql = """
    INSERT INTO audit_logs (actor_id, action, target_table, target_id, timestamp, details)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """
    try:
        execute_insert(sql, (actor_id, action, target_table, target_id, details))
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")


def create_notification(user_id: int, message: str) -> int:
    """Helper to dispatch an in-app notification to a user."""
    sql = """
    INSERT INTO notifications (user_id, message, is_read, created_at)
    VALUES (?, ?, 0, CURRENT_TIMESTAMP)
    """
    return execute_insert(sql, (user_id, message))


def init_db():
    """
    Initialize SQLite schema with relational constraints, foreign keys,
    check constraints, and performance indexes.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'organizer', 'admin')),
            category TEXT NOT NULL CHECK(category IN ('internal_verified', 'external')),
            full_name TEXT NOT NULL,
            phone TEXT,
            institution TEXT,
            department TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration: add avatar_url if table already existed without it
        cursor.execute("PRAGMA table_info(users)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        if "avatar_url" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")

        # 2. Events Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            description TEXT,
            banner_url TEXT,
            category TEXT NOT NULL,
            format TEXT NOT NULL CHECK(format IN ('In-Person', 'Online', 'Hybrid')),
            venue TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            reg_start TIMESTAMP NOT NULL,
            reg_end TIMESTAMP NOT NULL,
            capacity INTEGER NOT NULL CHECK(capacity > 0),
            internal_fee REAL NOT NULL DEFAULT 0.0 CHECK(internal_fee == 0.0),
            external_fee REAL NOT NULL DEFAULT 0.0 CHECK(external_fee >= 0.0),
            status TEXT NOT NULL CHECK(status IN (
                'Draft', 'Pending Approval', 'Approved', 'Rejected',
                'Published', 'Registration Open', 'Registration Closed',
                'Full', 'Ongoing', 'Completed', 'Cancelled'
            )),
            organizer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            admin_feedback TEXT,
            agenda TEXT,
            signatory_name TEXT,
            signatory_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. Registrations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            registration_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Registered', 'Cancelled', 'Attended')),
            payment_status TEXT NOT NULL CHECK(payment_status IN ('Completed', 'Pending', 'Failed', 'Exempt_Zero_Fee')),
            qr_code_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, user_id)
        );
        """)

        # 4. Payments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount REAL NOT NULL CHECK(amount >= 0.0),
            currency TEXT NOT NULL DEFAULT 'INR',
            transaction_id TEXT UNIQUE NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Success', 'Failed', 'Refunded')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 5. Attendance Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER UNIQUE NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
            scanned_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent'))
        );
        """)

        # 6. Certificates Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER UNIQUE NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
            certificate_id TEXT UNIQUE NOT NULL,
            issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL CHECK(status IN ('Issued', 'Revoked')),
            file_path TEXT NOT NULL
        );
        """)

        # 7. Audit Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            target_table TEXT NOT NULL,
            target_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        );
        """)

        # 8. Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0 CHECK(is_read IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_organizer ON events(organizer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_registrations_user ON registrations(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_registrations_event ON registrations(event_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_registrations_reg_id ON registrations(registration_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_reg ON payments(registration_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_reg ON attendance(registration_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_certificates_cert_id ON certificates(certificate_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);")


def seed_database():
    """
    Seeds initial realistic development data into the database.
    Creates default admin, organizers, internal/external students,
    sample events across all lifecycle statuses, registrations, and payments.
    """
    user_count = execute_query_one("SELECT COUNT(*) as count FROM users")
    if user_count and user_count["count"] > 0:
        return  # Database already seeded

    print("[SEED] Seeding development accounts and events...")

    # 1. Create Users
    users_data = [
        # Administrator
        ("admin@simats.edu", "Admin@123", "admin", "internal_verified", "SIMATS University Admin", "+91 94440 12345", "SIMATS Deemed University", "Central Administration"),
        # Organizers (Invited/created exclusively by Admin)
        ("organizer@simats.edu", "Organizer@123", "organizer", "internal_verified", "Dr. Ramesh Kumar", "+91 98840 54321", "SIMATS Engineering", "Computer Science & Engineering"),
        ("biotech.org@simats.edu", "Organizer@123", "organizer", "internal_verified", "Dr. Priya Sharma", "+91 97720 98765", "Saveetha Dental & Medical Sciences", "Biotechnology & Bioinformatics"),
        # Internal Verified Students (@simats.edu)
        ("arun.v@simats.edu", "Student@123", "student", "internal_verified", "Arun Venkat", "+91 98401 23456", "SIMATS Engineering", "Information Technology"),
        ("divya.s@simats.edu", "Student@123", "student", "internal_verified", "Divya Sundaram", "+91 99402 34567", "Saveetha School of Engineering", "Artificial Intelligence & Data Science"),
        # External Participants (Non @simats.edu)
        ("karthik.external@gmail.com", "External@123", "student", "external", "Karthik Raj", "+91 98412 87654", "Anna University", "Electronics & Communication"),
        ("sneha.p@vit.ac.in", "External@123", "student", "external", "Sneha Patel", "+91 97654 32109", "Vellore Institute of Technology", "Computer Science"),
    ]

    user_ids = {}
    for email, pwd, role, cat, name, phone, inst, dept in users_data:
        pwd_hash = hash_password(pwd)
        uid = execute_insert("""
        INSERT INTO users (email, password_hash, role, category, full_name, phone, institution, department)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, pwd_hash, role, cat, name, phone, inst, dept))
        user_ids[email] = uid
        log_audit(uid, "USER_INITIALIZED", "users", uid, f"Seed user {email} created with role {role}")

    admin_id = user_ids["admin@simats.edu"]
    org1_id = user_ids["organizer@simats.edu"]
    org2_id = user_ids["biotech.org@simats.edu"]

    # 2. Create Events across various lifecycle states
    now = datetime.datetime.now()
    
    events_data = [
        # 1. NEXUS '26: 24-Hour National AI & Full-Stack Hackathon
        (
            "NEXUS '26: 24-Hour National AI & Full-Stack Hackathon",
            "24-Hour National AI & Full-Stack Hackathon — Build. Innovate. Disrupt.",
            "NEXUS '26 brings together the nation's brightest developers, AI engineers, and full-stack innovators for a premier 24-hour sprint. Tackle cutting-edge challenges in artificial intelligence, autonomous agent workflows, generative models, and scalable systems. Featuring industry mentorship, compute clusters, and cash prizes.",
            "static/posters/nexus26.jpg",
            "Technical",
            "In-Person",
            "Round Building",
            "2026-11-20 09:00:00",
            "2026-11-21 17:00:00",
            "2026-11-01 00:00:00",
            "2026-11-19 23:59:59",
            150,
            0.0,
            500.0,
            "Registration Open",
            org1_id,
            "Approved. Flagship hackathon officially approved for university publication.",
            "Day 1 (Nov 20): 09:00 AM Registration & Inauguration, 10:00 AM Problem Statement Release & Hacking Begins, 04:00 PM Mentorship Round 1. Day 2 (Nov 21): 10:00 AM Final Evaluation, 03:00 PM Top 10 Pitches, 05:00 PM Awards Ceremony.",
            "Dr. Ramesh Kumar",
            "Convener & Head of Department, CSE, SIMATS Engineering"
        ),
        # 2. Zero-Trust Cybersecurity & Next-Gen Blockchain Bootcamp
        (
            "Zero-Trust Cybersecurity & Next-Gen Blockchain Bootcamp",
            "Hands-On Industry Certification Workshop in Zero-Trust Security & Blockchain Architecture.",
            "An intensive 3-day deep dive into modern zero-trust enterprise architecture, offensive defense simulation, smart contract security auditing, and decentralized ledger infrastructure. Participants gain hands-on penetration testing labs, cryptographic protocol design, and industry certification.",
            "static/posters/cybersecurity26.jpg",
            "Workshop",
            "In-Person",
            "SCAD Auditorium",
            "2026-12-14 09:00:00",
            "2026-12-16 17:00:00",
            "2026-11-01 00:00:00",
            "2026-12-13 23:59:59",
            120,
            0.0,
            750.0,
            "Registration Open",
            org1_id,
            "Approved by Academic Dean for national technical training.",
            "Day 1 (Dec 14): Zero-Trust Network Architecture & Threat Modeling. Day 2 (Dec 15): Blockchain Consensus, Smart Contracts & EVM Auditing. Day 3 (Dec 16): Live CTF Defense Drills, Exploit Analysis & Certificate Issuance.",
            "Dr. Ramesh Kumar",
            "Convener & Head of Department, CSE, SIMATS Engineering"
        ),
        # 3. SPANDAN '26: Annual Cultural & Arts Extravaganza
        (
            "SPANDAN '26: Annual Cultural & Arts Extravaganza",
            "Annual Cultural & Arts Extravaganza — Rhythm, Expression & Campus Spirit.",
            "The flagship university cultural spectacle of South India. SPANDAN '26 celebrates performing arts, classical and contemporary music showdowns, inter-collegiate dance battles, theatrical drama, fashion runways, and star-studded live pro-shows across three unforgettable days at Saveetha.",
            "static/posters/spandan26.jpg",
            "Cultural",
            "In-Person",
            "Nalli Arangam",
            "2027-02-12 10:00:00",
            "2027-02-14 22:00:00",
            "2026-11-01 00:00:00",
            "2027-02-11 23:59:59",
            500,
            0.0,
            1000.0,
            "Registration Open",
            org1_id,
            "Approved by Central Administration for university-wide gala.",
            "Day 1 (Feb 12): Classical & Western Music Battle, Fine Arts Expo. Day 2 (Feb 13): Choreo Night, Dance Battles, Theatrics. Day 3 (Feb 14): Grand Fashion Runway, Celebrity Pro-Show & Awards Gala.",
            "Dean of Student Affairs",
            "SIMATS Deemed University"
        )
    ]

    event_ids = []
    for ev in events_data:
        eid = execute_insert("""
        INSERT INTO events (
            title, summary, description, banner_url, category, format, venue,
            start_time, end_time, reg_start, reg_end, capacity, internal_fee,
            external_fee, status, organizer_id, admin_feedback, agenda,
            signatory_name, signatory_title
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ev)
        event_ids.append(eid)
        log_audit(admin_id, "EVENT_SEEDED", "events", eid, f"Seeded event {ev[0]} with status {ev[14]}")

    hackathon_id = event_ids[0]
    bootcamp_id = event_ids[3]  # Completed event

    # 3. Seed Registrations, Payments & Attendance for Completed Event (Bootcamp)
    # Internal student Arun registered for free
    reg_id_arun = execute_insert("""
    INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
    VALUES (?, ?, 'SIMATS-REG-2026-001', 'Attended', 'Exempt_Zero_Fee', datetime('now', '-9 days'))
    """, (bootcamp_id, user_ids["arun.v@simats.edu"]))

    # External student Karthik registered with paid fee ₹300
    reg_id_karthik = execute_insert("""
    INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
    VALUES (?, ?, 'SIMATS-REG-2026-002', 'Attended', 'Completed', datetime('now', '-9 days'))
    """, (bootcamp_id, user_ids["karthik.external@gmail.com"]))

    # Payment record for Karthik
    execute_insert("""
    INSERT INTO payments (registration_id, user_id, amount, currency, transaction_id, payment_method, status, created_at)
    VALUES (?, ?, 300.0, 'INR', 'TXN-SIMATS-2026-8812', 'UPI (Mock Simulator)', 'Success', datetime('now', '-9 days'))
    """, (reg_id_karthik, user_ids["karthik.external@gmail.com"]))

    # Attendance records
    execute_insert("""
    INSERT INTO attendance (registration_id, scanned_by, scanned_at, status)
    VALUES (?, ?, datetime('now', '-9 days', '+1 hour'), 'Present')
    """, (reg_id_arun, org1_id))

    execute_insert("""
    INSERT INTO attendance (registration_id, scanned_by, scanned_at, status)
    VALUES (?, ?, datetime('now', '-9 days', '+1 hour'), 'Present')
    """, (reg_id_karthik, org1_id))

    # Seed certificates for completed event
    execute_insert("""
    INSERT INTO certificates (registration_id, certificate_id, issue_date, status, file_path)
    VALUES (?, 'SIMATS-CERT-2026-001', datetime('now', '-8 days'), 'Issued', 'static/certificates/SIMATS-CERT-2026-001.pdf')
    """, (reg_id_arun,))

    execute_insert("""
    INSERT INTO certificates (registration_id, certificate_id, issue_date, status, file_path)
    VALUES (?, 'SIMATS-CERT-2026-002', datetime('now', '-8 days'), 'Issued', 'static/certificates/SIMATS-CERT-2026-002.pdf')
    """, (reg_id_karthik,))

    # 4. Seed Registrations for Upcoming Hackathon
    # Divya (Internal, ₹0)
    execute_insert("""
    INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
    VALUES (?, ?, 'SIMATS-REG-2026-003', 'Registered', 'Exempt_Zero_Fee', datetime('now', '-2 days'))
    """, (hackathon_id, user_ids["divya.s@simats.edu"]))

    # Sneha (External, ₹250)
    reg_id_sneha = execute_insert("""
    INSERT INTO registrations (event_id, user_id, registration_id, status, payment_status, created_at)
    VALUES (?, ?, 'SIMATS-REG-2026-004', 'Registered', 'Completed', datetime('now', '-1 days'))
    """, (hackathon_id, user_ids["sneha.p@vit.ac.in"]))

    execute_insert("""
    INSERT INTO payments (registration_id, user_id, amount, currency, transaction_id, payment_method, status, created_at)
    VALUES (?, ?, 250.0, 'INR', 'TXN-SIMATS-2026-9934', 'Credit Card (Mock Simulator)', 'Success', datetime('now', '-1 days'))
    """, (reg_id_sneha, user_ids["sneha.p@vit.ac.in"]))

    # 5. Notifications
    create_notification(user_ids["arun.v@simats.edu"], "Welcome to SIMATS Event Sphere! Your internal student status has been verified.")
    create_notification(user_ids["arun.v@simats.edu"], "Certificate issued for 'Web3 & Smart Contract Security Bootcamp'. You may download it from your dashboard.")
    create_notification(user_ids["divya.s@simats.edu"], "Registration confirmed for 'SIMATS National Hackathon 2026 - HackSphere'. Your QR ticket is ready.")
    create_notification(user_ids["karthik.external@gmail.com"], "Payment received: ₹300.00 for Web3 Bootcamp. Receipt #TXN-SIMATS-2026-8812.")
    create_notification(user_ids["sneha.p@vit.ac.in"], "Payment received: ₹250.00 for SIMATS National Hackathon 2026. Receipt #TXN-SIMATS-2026-9934.")
    create_notification(org2_id, "Your event 'International Workshop on CRISPR' has been submitted for Administrator review.")

    print("[SEED] Successfully seeded development database.")


# Initialize and seed upon first import or direct run
init_db()
seed_database()

if __name__ == "__main__":
    print(f"Database initialized at: {DB_PATH}")
    print(f"Total Users: {execute_query_one('SELECT COUNT(*) as c FROM users')['c']}")
    print(f"Total Events: {execute_query_one('SELECT COUNT(*) as c FROM events')['c']}")
    print(f"Total Registrations: {execute_query_one('SELECT COUNT(*) as c FROM registrations')['c']}")
    print(f"Total Payments: {execute_query_one('SELECT COUNT(*) as c FROM payments')['c']}")
