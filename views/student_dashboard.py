"""
SIMATS Event Sphere - Student / Participant Dashboard View Module
Handles participant registration discovery, 1-Click ₹0 waiver, Mock Payment Simulator,
visual QR tickets, attendance verification status, dynamic PDF certificate generation,
and notification center.
Enforces tight, balanced layout and strict local asset usage.
"""

import os
import streamlit as st
import datetime
from database import (
    execute_query,
    execute_query_one,
    execute_write,
    STATIC_DIR,
    AVATARS_DIR
)
from auth import get_current_user, update_user_profile
from event_service import get_public_events, EVENT_CATEGORIES
from payment_service import (
    register_internal_student_instant,
    process_external_mock_payment,
    check_registration_eligibility
)
from certificate_service import generate_certificate, check_certificate_eligibility
from qr_service import generate_ticket_qr
from asset_helper import (
    ASSETS,
    get_event_poster_path,
    get_image_base64,
    get_user_avatar_html,
    render_html,
    clean_html
)


def render_student_dashboard():
    """Render the full student / participant dashboard."""
    user = get_current_user()
    if not user:
        st.warning("Please log in to access the participant dashboard.")
        return

    is_internal = (user.get("category") == "internal_verified")
    logo_b64 = get_image_base64(ASSETS["logo_college"])

    # Header banner with user role badge and university branding
    if is_internal:
        badge_html = '<span class="simats-badge badge-internal" style="font-size: 0.8rem;">🎓 SIMATS Verified Student &bull; ₹0.00 Fee Waiver</span>'
    else:
        badge_html = f'<span class="simats-badge badge-external" style="font-size: 0.8rem;">🌐 External Participant &bull; {user.get("institution", "External")}</span>'

    avatar_html = get_user_avatar_html(user, size=48)

    render_html(
        f'<div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">'
        f'<div style="display: flex; align-items: center; gap: 12px;">'
        f'<img src="{logo_b64}" style="height: 44px; width: auto;" alt="SIMATS"/>'
        f'<div>'
        f'<h2 style="margin: 0; color: #0A2540; font-size: 1.45rem;">Participant Portal: {user["full_name"]}</h2>'
        f'<p style="margin: 2px 0 0 0; color: #64748B; font-size: 0.85rem;">{user["email"]} &nbsp;|&nbsp; {user.get("department") or "Student"}</p>'
        f'</div>'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 12px;">'
        f'{badge_html}'
        f'{avatar_html}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # Active tab state handling
    default_tab_index = 0
    if st.session_state.get("student_active_tab") == "Event Registration & Discovery":
        default_tab_index = 2
    elif st.session_state.get("student_active_tab") == "My Certificates":
        default_tab_index = 1

    tabs = st.tabs([
        "🎫 My Registrations & QR Tickets",
        "📜 My Certificates",
        "🔍 Browse & Register for Events",
        "🔔 Notifications",
        "⚙️ Profile Settings"
    ])

    # ---------------- TAB 1: REGISTRATIONS & TICKETS ----------------
    with tabs[0]:
        st.markdown("<h4 style='color: #0A2540; margin: 0 0 6px 0;'>My Event Tickets &amp; QR Passes</h4>", unsafe_allow_html=True)
        
        my_regs = execute_query("""
        SELECT r.id as reg_db_id, r.registration_id, r.status as reg_status, r.payment_status,
               r.qr_code_path, r.created_at as registered_on,
               e.id as event_id, e.title as event_title, e.format as event_format,
               e.start_time, e.end_time, e.venue, e.status as event_status, e.category as event_category,
               a.status as attendance_status, a.scanned_at,
               p.amount as paid_amount, p.transaction_id, p.payment_method
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        LEFT JOIN attendance a ON r.id = a.registration_id
        LEFT JOIN payments p ON r.id = p.registration_id AND p.status = 'Success'
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
        """, (user["id"],))

        if not my_regs:
            st.info("You haven't registered for any events yet. Check the 'Browse & Register for Events' tab to discover campus events!")
        else:
            for reg in my_regs:
                with st.container():
                    attendance_div = (
                        f'<div style="margin-top: 6px; color: #065F46; font-size: 0.82rem; font-weight: 600;">✅ Attendance Verified: Checked in at {reg["scanned_at"]}</div>'
                        if reg['attendance_status'] == 'Present'
                        else '<div style="margin-top: 6px; color: #D97706; font-size: 0.82rem; font-weight: 600;">⏳ Gate Pass Ready: Present this QR code at event check-in</div>'
                    )
                    render_html(
                        f'<div class="ticket-container" style="margin-top: 0.5rem; margin-bottom: 0.75rem;">'
                        f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">'
                        f'<div style="flex: 2; min-width: 260px;">'
                        f'<div style="display: flex; gap: 6px; margin-bottom: 4px;">'
                        f'<span class="simats-badge badge-internal">{reg["event_format"]}</span>'
                        f'<span class="simats-badge {"badge-status-completed" if reg["reg_status"] == "Attended" else "badge-status-open"}">Status: {reg["reg_status"]}</span>'
                        f'<span class="simats-badge badge-external">Fee: {reg["payment_status"]}</span>'
                        f'</div>'
                        f'<h3 style="margin: 0 0 4px 0; color: #0A2540; font-size: 1.2rem;">{reg["event_title"]}</h3>'
                        f'<p style="margin: 0 0 8px 0; color: #64748B; font-size: 0.85rem;"><strong>Registration Pass ID:</strong> <code style="font-size: 0.95rem; color: #1B365D;">{reg["registration_id"]}</code></p>'
                        f'<div style="display: flex; gap: 14px; font-size: 0.8rem; color: #475569; flex-wrap: wrap;">'
                        f'<div>📅 <strong>Date:</strong> {reg["start_time"][:16]}</div>'
                        f'<div>📍 <strong>Venue:</strong> {reg["venue"]}</div>'
                        f'<div>💳 <strong>Amount:</strong> ₹{reg["paid_amount"] or 0.0} ({reg["payment_method"] or "Waiver"})</div>'
                        f'</div>'
                        f'{attendance_div}'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )

                    # Ticket QR Code display & download
                    col_qr_disp, col_qr_act = st.columns([1, 4])
                    
                    # Ensure QR file exists
                    qr_rel_path = reg.get("qr_code_path")
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    full_qr_path = os.path.join(base_dir, qr_rel_path.replace("/", os.sep)) if qr_rel_path else None

                    if not full_qr_path or not os.path.exists(full_qr_path):
                        qr_rel_path = generate_ticket_qr(reg["registration_id"], reg["event_id"], user["id"])
                        full_qr_path = os.path.join(base_dir, qr_rel_path.replace("/", os.sep))

                    with col_qr_disp:
                        if os.path.exists(full_qr_path):
                            st.image(full_qr_path, width=130, caption=f"{reg['registration_id']}")

                    with col_qr_act:
                        st.markdown("**Visual Tamper-Resistant QR Pass**")
                        st.caption("Present this cryptographically generated QR ticket at the venue check-in desk.")
                        if os.path.exists(full_qr_path):
                            with open(full_qr_path, "rb") as f:
                                st.download_button(
                                    label="💾 Download Ticket Gate Pass (PNG)",
                                    data=f.read(),
                                    file_name=f"SIMATS-TICKET-{reg['registration_id']}.png",
                                    mime="image/png",
                                    key=f"dl_qr_{reg['reg_db_id']}"
                                )
                    st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # ---------------- TAB 2: MY CERTIFICATES ----------------
    with tabs[1]:
        st.markdown("<h4 style='color: #0A2540; margin: 0 0 4px 0;'>Official University Certificates</h4>", unsafe_allow_html=True)
        st.caption("ℹ️ **Issuance Rule:** Verified certificates unlock strictly after event completion and verified organizer attendance.")

        completed_registrations = execute_query("""
        SELECT r.id as reg_db_id, r.registration_id, r.status as reg_status,
               e.id as event_id, e.title as event_title, e.status as event_status,
               e.start_time, e.venue,
               a.status as attendance_status, a.scanned_at,
               c.certificate_id, c.file_path, c.issue_date as cert_issue_date
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        LEFT JOIN attendance a ON r.id = a.registration_id
        LEFT JOIN certificates c ON r.id = c.registration_id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
        """, (user["id"],))

        if not completed_registrations:
            st.write("No event registrations found.")
        else:
            for item in completed_registrations:
                eligible, el_msg, _ = check_certificate_eligibility(item["registration_id"])
                
                with st.container():
                    eligible_badge = '<span class="simats-badge badge-status-completed">✅ Eligible for Certificate</span>' if eligible else '<span class="simats-badge badge-status-draft">🔒 Locked</span>'
                    render_html(
                        f'<div class="simats-card" style="margin-bottom: 0.5rem;">'
                        f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">'
                        f'<div>'
                        f'<h4 style="margin: 0; color: #0A2540; font-size: 1.15rem;">{item["event_title"]}</h4>'
                        f'<div style="display: flex; gap: 12px; font-size: 0.8rem; color: #64748B; margin-top: 2px;">'
                        f'<span>Event Status: <strong>{item["event_status"]}</strong></span>'
                        f'<span>Attendance: <strong>{item["attendance_status"] or "Unverified / Absent"}</strong></span>'
                        f'</div>'
                        f'</div>'
                        f'<div>{eligible_badge}</div>'
                        f'</div>'
                        f'</div>'
                    )

                    if eligible:
                        col_c1, col_c2 = st.columns([2, 2])
                        with col_c1:
                            if st.button("Generate / Retrieve Official Certificate", key=f"btn_gen_cert_{item['reg_db_id']}", type="primary"):
                                ok, msg, pdf_rel_path, cert_id = generate_certificate(item["registration_id"])
                                if ok:
                                    st.success(f"Certificate ready! Certificate ID: **{cert_id}**")
                                    st.session_state[f"cert_ready_{item['reg_db_id']}"] = (pdf_rel_path, cert_id)
                                    st.rerun()
                                else:
                                    st.error(msg)

                        with col_c2:
                            cert_data = st.session_state.get(f"cert_ready_{item['reg_db_id']}") or (item.get("file_path"), item.get("certificate_id"))
                            if cert_data and cert_data[0]:
                                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                full_cert_path = os.path.join(base_dir, cert_data[0].replace("/", os.sep))
                                if os.path.exists(full_cert_path):
                                    with open(full_cert_path, "rb") as f:
                                        st.download_button(
                                            label=f"📄 Download Certificate ({cert_data[1]})",
                                            data=f.read(),
                                            file_name=f"{cert_data[1]}.pdf",
                                            mime="application/pdf",
                                            key=f"dl_btn_{item['reg_db_id']}"
                                        )
                    else:
                        st.caption(f"Reason: {el_msg}")
                    st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # ---------------- TAB 3: BROWSE & REGISTER FOR EVENTS ----------------
    with tabs[2]:
        st.markdown("<h4 style='color: #0A2540; margin: 0 0 6px 0;'>Register for Upcoming Events</h4>", unsafe_allow_html=True)
        
        open_events = get_public_events(date_filter="Upcoming")
        
        if not open_events:
            st.info("No upcoming events currently open for registration.")
        else:
            for ev in open_events:
                eligible, el_msg, details = check_registration_eligibility(user["id"], ev["id"])
                poster_path = get_event_poster_path(ev)
                poster_b64 = get_image_base64(poster_path)
                fee_tag = "₹0.00 (SIMATS Waiver)" if is_internal or ev["external_fee"] == 0 else f"₹{int(ev['external_fee'])}"
                seats_left = max(0, ev["capacity"] - ev["registered_count"])

                with st.container():
                    # 1. THUMBNAIL / SUMMARY CARD VIEW
                    render_html(
                        f'<div class="simats-card" style="margin-bottom: 0.6rem; padding: 14px 18px; border-radius: 10px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 2px 8px rgba(10,37,64,0.04);">'
                        f'<div style="display: flex; gap: 18px; align-items: center; flex-wrap: wrap;">'
                        f'<div style="flex: 0 0 140px; max-width: 140px; border-radius: 8px; overflow: hidden; border: 1px solid #CBD5E1; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">'
                        f'<img src="{poster_b64}" style="width: 100%; height: 105px; object-fit: cover; display: block;" alt="{ev["title"]} Thumbnail"/>'
                        f'</div>'
                        f'<div style="flex: 1; min-width: 260px;">'
                        f'<div style="display: flex; gap: 6px; margin-bottom: 4px; flex-wrap: wrap;">'
                        f'<span class="simats-badge badge-internal">{ev["category"]}</span>'
                        f'<span class="simats-badge badge-external">{ev["format"]}</span>'
                        f'<span class="simats-badge badge-status-open">{ev.get("effective_status", ev.get("status", "Open"))}</span>'
                        f'</div>'
                        f'<h3 style="margin: 2px 0 6px 0; color: #0A2540; font-size: 1.2rem; font-weight: 700;">{ev["title"]}</h3>'
                        f'<p style="font-size: 0.88rem; color: #475569; margin: 0 0 8px 0; line-height: 1.35;">{ev["summary"] or (ev["description"][:120] + "...")}</p>'
                        f'<div style="display: flex; gap: 16px; font-size: 0.82rem; color: #64748B; flex-wrap: wrap;">'
                        f'<div>📅 <strong>Date:</strong> {ev["start_time"][:16]}</div>'
                        f'<div>📍 <strong>Venue:</strong> {ev["venue"]}</div>'
                        f'<div>👥 <strong>Seats:</strong> {seats_left}/{ev["capacity"]} Available</div>'
                        f'</div>'
                        f'</div>'
                        f'<div style="text-align: right; min-width: 150px; border-left: 1px dashed #E2E8F0; padding-left: 16px;">'
                        f'<div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Your Applicable Fee</div>'
                        f'<div style="font-size: 1.25rem; font-weight: 800; color: {"#065F46" if is_internal or ev["external_fee"] == 0 else "#0A2540"}; margin: 2px 0 6px 0;">{fee_tag}</div>'
                        f'<div style="font-size: 0.72rem; color: #94A3B8;">Click details below to expand</div>'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )

                    # 2. EXPANDABLE FULL DETAILS VIEW (ON CLICK / EXPANDER)
                    with st.expander(f"📋 Expand Full Poster, Agenda & Registration — {ev['title']}", expanded=False):
                        # (A) Full-sized high-resolution poster image prominently displayed
                        render_html(
                            f'<div style="margin-bottom: 12px; border-radius: 10px; overflow: hidden; border: 1px solid #CBD5E1; box-shadow: 0 4px 14px rgba(10,37,64,0.08);">'
                            f'<img src="{poster_b64}" style="width: 100%; height: auto; max-height: 820px; object-fit: contain; display: block; background: #0A192F;" alt="{ev["title"]} Full Poster"/>'
                            f'</div>'
                        )

                        # (B) Full event description, venue, and detailed metadata directly below the poster
                        st.markdown(f"#### 📖 About {ev['title']}")
                        render_html(f'<div style="font-size: 0.95rem; line-height: 1.6; color: #334155; margin-bottom: 1rem;">{ev["description"]}</div>')

                        # Detailed metadata columns
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            render_html(
                                f'<div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 10px; font-size: 0.88rem;">'
                                f'<div><strong>📍 Official Venue:</strong> {ev["venue"]}</div>'
                                f'<div style="margin-top: 4px;"><strong>📅 Event Schedule:</strong> {ev["start_time"]} to {ev["end_time"]}</div>'
                                f'<div style="margin-top: 4px;"><strong>⏳ Registration Window:</strong> {ev["reg_start"]} to {ev["reg_end"]}</div>'
                                f'</div>'
                            )

                        with col_m2:
                            render_html(
                                f'<div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 10px; font-size: 0.88rem;">'
                                f'<div><strong>🏷️ Category &amp; Format:</strong> {ev["category"]} ({ev["format"]})</div>'
                                f'<div style="margin-top: 4px;"><strong>👥 Seat Capacity:</strong> {seats_left} seats remaining of {ev["capacity"]} total</div>'
                                f'<div style="margin-top: 4px;"><strong>👨‍🏫 Faculty Organizer:</strong> {ev.get("organizer_name", "SIMATS Faculty Office")}</div>'
                                f'</div>'
                            )

                        if ev.get("agenda"):
                            st.markdown("#### 📅 Event Schedule & Agenda")
                            render_html(f'<div style="background: #F1F5F9; border-left: 3px solid #C5A059; padding: 10px 14px; border-radius: 4px; font-size: 0.88rem; color: #1E293B; margin-bottom: 1rem; white-space: pre-wrap;">{ev["agenda"]}</div>')

                        if ev.get("signatory_name"):
                            st.caption(f"📜 Verified Certificate Signatory: **{ev['signatory_name']}**, {ev.get('signatory_title', '')}")

                        st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

                        # (C) Registration button positioned clearly at the very bottom
                        st.markdown("#### 🎟️ Event Registration")

                        if not eligible:
                            if "already registered" in el_msg.lower():
                                st.success(f"✅ {el_msg}")
                            else:
                                st.warning(f"Registration Notice: {el_msg}")
                        else:
                            if is_internal or ev["external_fee"] == 0:
                                st.info("✨ **SIMATS Institutional Benefit:** Your permanent ₹0.00 fee waiver is automatically applied. Instant registration issues your visual QR gate pass immediately.")
                                if st.button(f"⚡ Confirm Instant Registration (₹0.00)", key=f"btn_reg_internal_{ev['id']}", type="primary", use_container_width=True):
                                    ok, msg, reg_data = register_internal_student_instant(user["id"], ev["id"])
                                    if ok:
                                        st.success(msg)
                                        st.session_state["student_active_tab"] = "🎫 My Registrations & QR Tickets"
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                render_html(
                                    f'<div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; margin-bottom: 12px;">'
                                    f'<strong style="color: #0A2540;">External Participant Checkout — Fee: ₹{int(ev["external_fee"])}</strong><br/>'
                                    f'<span style="font-size: 0.82rem; color: #64748B;">Test external registration payment simulation with automatic transaction recording and receipt generation.</span>'
                                    f'</div>'
                                )

                                pay_method = st.radio(
                                    "Select Payment Method",
                                    ["UPI (GPay / PhonePe / Paytm)", "Credit / Debit Card", "Net Banking"],
                                    key=f"pay_meth_{ev['id']}",
                                    horizontal=True
                                )

                                col_inp1, col_inp2 = st.columns(2)
                                with col_inp1:
                                    if "UPI" in pay_method:
                                        st.text_input("Simulated UPI ID", value="participant@okaxis", key=f"upi_inp_{ev['id']}")
                                    else:
                                        st.text_input("Simulated Card Number", value="4532 •••• •••• 8821", key=f"card_inp_{ev['id']}")
                                with col_inp2:
                                    st.text_input("Name on Account", value=user["full_name"], key=f"name_inp_{ev['id']}")

                                col_btn_succ, col_btn_fail = st.columns(2)
                                with col_btn_succ:
                                    if st.button(f"✅ Pay ₹{int(ev['external_fee'])} & Confirm Registration", key=f"btn_pay_succ_{ev['id']}", type="primary", use_container_width=True):
                                        ok, msg, data = process_external_mock_payment(
                                            user_id=user["id"],
                                            event_id=ev["id"],
                                            payment_method=pay_method,
                                            simulate_success=True
                                        )
                                        if ok:
                                            st.success(msg)
                                            st.session_state["student_active_tab"] = "🎫 My Registrations & QR Tickets"
                                            st.rerun()
                                        else:
                                            st.error(msg)

                                with col_btn_fail:
                                    if st.button("❌ Simulate Payment Failure", key=f"btn_pay_fail_{ev['id']}", use_container_width=True):
                                        ok, msg, data = process_external_mock_payment(
                                            user_id=user["id"],
                                            event_id=ev["id"],
                                            payment_method=pay_method,
                                            simulate_success=False
                                        )
                                        st.error(msg)

                    st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # ---------------- TAB 4: NOTIFICATIONS ----------------
    with tabs[3]:
        st.markdown("<h4 style='color: #0A2540; margin: 0 0 6px 0;'>In-App Notification Center</h4>", unsafe_allow_html=True)
        
        c_notif_head, c_notif_act = st.columns([3, 1])
        with c_notif_act:
            if st.button("Mark All as Read", key="btn_mark_all_read"):
                execute_write("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
                st.success("All notifications marked as read.")
                st.rerun()

        notifications = execute_query("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        """, (user["id"],))

        if not notifications:
            st.info("No notifications at this time.")
        else:
            for notif in notifications:
                unread_indicator = "🔵 " if not notif["is_read"] else ""
                render_html(
                    f'<div style="background: {"#F0FDF4" if not notif["is_read"] else "#FFFFFF"}; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px;">'
                    f'<div style="font-size: 0.9rem; color: #0F172A;">{unread_indicator}{notif["message"]}</div>'
                    f'<div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">{notif["created_at"]}</div>'
                    f'</div>'
                )

    # ---------------- TAB 5: PROFILE SETTINGS ----------------
    with tabs[4]:
        st.markdown("<h4 style='color: #0A2540; margin: 0 0 6px 0;'>Profile Settings</h4>", unsafe_allow_html=True)
        st.info("ℹ️ **Security Rule:** Internal verified status (`@simats.edu`) and participant roles are immutable to protect billing integrity.")

        col_sp1, col_sp2 = st.columns([1, 2])
        with col_sp1:
            avatar_large = get_user_avatar_html(user, size=84)
            render_html(
                f'<div style="text-align: center; padding: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; margin-bottom: 12px;">'
                f'<div style="margin-bottom: 8px;">{avatar_large}</div>'
                f'<div style="font-weight: 700; color: #0A2540; font-size: 1.05rem;">{user["full_name"]}</div>'
                f'<div style="font-size: 0.8rem; color: #64748B;">{user["email"]}</div>'
                f'<div style="margin-top: 6px;">{badge_html}</div>'
                f'</div>'
            )

        with col_sp2:
            with st.form("student_profile_form"):
                prof_name = st.text_input("Full Name", value=user["full_name"])
                prof_phone = st.text_input("Phone Number", value=user.get("phone") or "")
                prof_inst = st.text_input("Institution", value=user.get("institution") or "", disabled=is_internal)
                prof_dept = st.text_input("Department / Specialization", value=user.get("department") or "")

                stud_avatar_file = st.file_uploader(
                    "Upload / Replace Profile Photo (PNG/JPG)",
                    type=["png", "jpg", "jpeg"],
                    key="uploader_student_avatar",
                    help="Upload a custom profile photo. Stored securely on the local server."
                )
                
                submit_prof = st.form_submit_button("Save Profile Changes", type="primary")
                if submit_prof:
                    new_avatar_rel = user.get("avatar_url")
                    if stud_avatar_file is not None:
                        os.makedirs(AVATARS_DIR, exist_ok=True)
                        avatar_filename = f"avatar_user_{user['id']}_{int(datetime.datetime.now().timestamp())}_{stud_avatar_file.name.replace(' ', '_')}"
                        avatar_abs_path = os.path.join(AVATARS_DIR, avatar_filename)
                        with open(avatar_abs_path, "wb") as af:
                            af.write(stud_avatar_file.getbuffer())
                        new_avatar_rel = f"static/avatars/{avatar_filename}"

                    ok, msg = update_user_profile(
                        user_id=user["id"],
                        full_name=prof_name,
                        phone=prof_phone,
                        institution=prof_inst,
                        department=prof_dept,
                        avatar_url=new_avatar_rel
                    )
                    if ok:
                        st.success(msg)
                        refreshed = execute_query_one("SELECT * FROM users WHERE id = ?", (user["id"],))
                        st.session_state["user"] = dict(refreshed)
                        st.rerun()
                    else:
                        st.error(msg)
