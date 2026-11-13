"""
SIMATS Event Sphere - PDF Certificate Generation & Public Verification Module
Server-side generation of tamper-evident university certificates using fpdf2.
Certificates are locked until event completion and attendance verification,
and protected against duplicate issuance.
"""

import os
import datetime
import uuid
import qrcode
from fpdf import FPDF

from database import (
    CERT_DIR,
    STATIC_DIR,
    execute_query_one,
    execute_insert,
    execute_write,
    log_audit,
    create_notification
)


def clean_latin(text: str) -> str:
    """Sanitizes unicode punctuation to standard ASCII for Helvetica rendering."""
    if not text:
        return ""
    replacements = {
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "₹": "INR ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class SIMATSCertificatePDF(FPDF):
    """Custom PDF generator for SIMATS University certificates."""
    def draw_borders(self):
        # Outer Navy border
        self.set_draw_color(27, 54, 93)  # #1B365D
        self.set_line_width(2.0)
        self.rect(8, 8, 281, 194)

        # Inner Gold border
        self.set_draw_color(197, 160, 89)  # #C5A059
        self.set_line_width(0.8)
        self.rect(12, 12, 273, 186)


def check_certificate_eligibility(registration_id: str) -> tuple[bool, str, dict | None]:
    """
    Checks if a student is eligible for a certificate.
    Rules:
    - Event must have status 'Completed'.
    - Student attendance record must exist with status 'Present'.
    """
    sql = """
    SELECT r.id as reg_db_id, r.registration_id, r.event_id, r.user_id, r.status as reg_status,
           e.title as event_title, e.category as event_category, e.start_time, e.end_time,
           e.venue, e.status as event_status, e.signatory_name, e.signatory_title,
           u.full_name as recipient_name, u.institution as recipient_institution,
           a.status as attendance_status, a.scanned_at,
           c.certificate_id, c.file_path, c.issue_date as cert_issue_date
    FROM registrations r
    JOIN events e ON r.event_id = e.id
    JOIN users u ON r.user_id = u.id
    LEFT JOIN attendance a ON r.id = a.registration_id
    LEFT JOIN certificates c ON r.id = c.registration_id
    WHERE r.registration_id = ?
    """
    data = execute_query_one(sql, (registration_id,))
    if not data:
        return False, "Registration record not found.", None

    if data["event_status"] != "Completed":
        return False, f"Certificate Locked: Event '{data['event_title']}' has not concluded yet (Current status: {data['event_status']}). Certificates are issued only upon event completion.", data

    if not data["attendance_status"] or data["attendance_status"] != "Present":
        return False, f"Certificate Locked: Attendance verification required. You have not been marked 'Present' for this event.", data

    return True, "Certificate eligible.", data


def generate_certificate(registration_id: str) -> tuple[bool, str, str | None, str | None]:
    """
    Generates dynamic server-side PDF certificate using fpdf2.
    - Locks until event is Completed and Attendance is Present.
    - Prevents duplicate issuance by reusing existing certificate.
    Returns: (success, message, file_path, certificate_id)
    """
    eligible, msg, data = check_certificate_eligibility(registration_id)
    if not eligible:
        return False, msg, None, None

    # Check if certificate record exists
    existing_cert_id = data.get("certificate_id")
    if existing_cert_id and data.get("file_path"):
        full_existing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), data["file_path"].replace("/", os.sep))
        if os.path.exists(full_existing_path):
            return True, "Certificate already generated.", data["file_path"], existing_cert_id

    now = datetime.datetime.now()
    cert_id = existing_cert_id if existing_cert_id else f"SIMATS-CERT-{now.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    pdf_filename = f"{cert_id}.pdf"
    pdf_path = os.path.join(CERT_DIR, pdf_filename)
    rel_path = f"static/certificates/{pdf_filename}"

    # Generate small verification QR code to embed in the certificate
    qr_payload = f"SIMATS-VERIFY:{cert_id}"
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1B365D", back_color="white")
    temp_qr_path = os.path.join(CERT_DIR, f"temp_qr_{cert_id}.png")
    qr_img.save(temp_qr_path)

    try:
        # Create Landscape A4 Certificate
        pdf = SIMATSCertificatePDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False, margin=10)
        pdf.add_page()
        pdf.draw_borders()

        # University Header
        pdf.set_y(20)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(27, 54, 93)  # Navy
        pdf.cell(0, 8, "SAVEETHA INSTITUTE OF MEDICAL AND TECHNICAL SCIENCES", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(197, 160, 89)  # Gold
        pdf.cell(0, 6, "SIMATS DEEMED UNIVERSITY - CHENNAI, INDIA", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)
        # Decorative divider line
        pdf.set_draw_color(197, 160, 89)
        pdf.set_line_width(0.5)
        pdf.line(40, pdf.get_y(), 257, pdf.get_y())
        pdf.ln(6)

        # Title
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(27, 54, 93)
        pdf.cell(0, 10, "CERTIFICATE OF PARTICIPATION", align="C", new_x="LMARGIN", new_y="NEXT")

        # Subtitle
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, "This is proudly presented to", align="C", new_x="LMARGIN", new_y="NEXT")

        # Recipient Name
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(15, 23, 42)
        recipient_display = clean_latin(data["recipient_name"].upper())
        pdf.cell(0, 10, recipient_display, align="C", new_x="LMARGIN", new_y="NEXT")

        # Affiliation / Institution
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(100, 116, 139)
        inst_text = clean_latin(f"from {data['recipient_institution']}" if data.get("recipient_institution") else "SIMATS Student Participant")
        pdf.cell(0, 6, inst_text, align="C", new_x="LMARGIN", new_y="NEXT")

        # Body Text
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 6, "for active participation and successful completion of the requirements in the university event", align="C", new_x="LMARGIN", new_y="NEXT")

        # Event Title
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(27, 54, 93)
        pdf.cell(0, 8, f'"{clean_latin(data["event_title"])}"', align="C", new_x="LMARGIN", new_y="NEXT")

        # Dates & Venue
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 116, 139)
        venue_str = clean_latin(f"Held at: {data['venue']}")
        pdf.cell(0, 5, venue_str, align="C", new_x="LMARGIN", new_y="NEXT")

        # Footer Area: QR code on Left, Certificate ID in Center, Signatory on Right
        footer_y = 152
        pdf.set_y(footer_y)

        # Embedded QR Code on left
        if os.path.exists(temp_qr_path):
            pdf.image(temp_qr_path, x=22, y=footer_y - 2, w=28, h=28)

        # QR Caption
        pdf.set_xy(20, footer_y + 27)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(32, 4, "Scan to Verify Authenticity", align="C")

        # Middle Metadata
        pdf.set_xy(60, footer_y + 5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(27, 54, 93)
        pdf.cell(110, 5, f"Certificate ID: {cert_id}", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(60, footer_y + 11)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(110, 4, f"Issued Date: {now.strftime('%d %B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(60, footer_y + 16)
        pdf.cell(110, 4, "SIMATS Central Office of Academic Affairs", align="C")

        # Signatory on Right
        signatory_name = clean_latin(data.get("signatory_name") or "Authorized University Signatory")
        signatory_title = clean_latin(data.get("signatory_title") or "Dean / Director, SIMATS")

        pdf.set_xy(185, footer_y + 10)
        pdf.set_draw_color(197, 160, 89)
        pdf.set_line_width(0.4)
        pdf.line(185, footer_y + 12, 270, footer_y + 12)

        pdf.set_xy(185, footer_y + 14)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(27, 54, 93)
        pdf.cell(85, 5, signatory_name, align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(185, footer_y + 19)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(85, 4, signatory_title, align="C")

        # Output PDF
        pdf.output(pdf_path)

        # Save to database
        if existing_cert_id:
            execute_write("""
            UPDATE certificates SET file_path = ?, status = 'Issued' WHERE certificate_id = ?
            """, (rel_path, cert_id))
        else:
            execute_insert("""
            INSERT INTO certificates (registration_id, certificate_id, issue_date, status, file_path)
            VALUES (?, ?, CURRENT_TIMESTAMP, 'Issued', ?)
            """, (data["reg_db_id"], cert_id, rel_path))

        log_audit(data["user_id"], "CERTIFICATE_GENERATED", "certificates", data["reg_db_id"], f"Certificate {cert_id} generated for {data['recipient_name']}")
        create_notification(data["user_id"], f"Official Certificate generated for '{data['event_title']}'! Cert ID: {cert_id}.")

        return True, "Official Certificate generated successfully!", rel_path, cert_id

    except Exception as e:
        return False, f"Failed to generate certificate PDF: {str(e)}", None, None
    finally:
        # Clean up temporary QR image
        if os.path.exists(temp_qr_path):
            try:
                os.remove(temp_qr_path)
            except Exception:
                pass


def verify_certificate_public(certificate_id: str) -> tuple[bool, str, dict | None]:
    """
    Public verification endpoint query:
    Confirms certificate authenticity and returns safe verification metadata
    without disclosing private data (passwords, phone numbers, email addresses).
    """
    clean_id = certificate_id.strip()
    sql = """
    SELECT c.certificate_id, c.issue_date, c.status as cert_status,
           u.full_name as recipient_name, u.institution,
           e.title as event_title, e.category as event_category, e.start_time, e.end_time,
           e.venue, e.signatory_name, e.signatory_title
    FROM certificates c
    JOIN registrations r ON c.registration_id = r.id
    JOIN users u ON r.user_id = u.id
    JOIN events e ON r.event_id = e.id
    WHERE c.certificate_id = ?
    """
    row = execute_query_one(sql, (clean_id,))
    if not row:
        return False, f"Verification Failed: Certificate ID '{clean_id}' does not exist in the official SIMATS registry.", None

    if row["cert_status"] != "Issued":
        return False, f"Certificate '{clean_id}' is marked as {row['cert_status'].upper()} and is no longer valid.", None

    result = {
        "certificate_id": row["certificate_id"],
        "recipient_name": row["recipient_name"],
        "institution": row["institution"] or "SIMATS Deemed University",
        "event_title": row["event_title"],
        "event_category": row["event_category"],
        "event_date": row["start_time"],
        "issue_date": row["issue_date"],
        "status": "VALID & AUTHENTIC",
        "signatory": f"{row['signatory_name']} ({row['signatory_title']})"
    }
    return True, "Certificate verified as authentic.", result
