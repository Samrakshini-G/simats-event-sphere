"""
SIMATS Event Sphere - Organizer Dashboard View Module
Provides event creation wizard, lifecycle state transitions, material modification checks,
participant roster management with CSV export, live QR camera attendance scanner,
and coordinator profile photo settings.
"""

import os
import textwrap
import datetime
import pandas as pd
import streamlit as st
from database import (
    execute_query,
    execute_query_one,
    execute_write,
    STATIC_DIR,
    AVATARS_DIR
)
from auth import get_current_user, update_user_profile
from event_service import (
    create_event,
    update_event,
    submit_draft_for_approval,
    publish_event,
    set_event_status,
    EVENT_CATEGORIES,
    EVENT_FORMATS,
    get_effective_status
)
from qr_service import decode_qr_image, verify_and_check_in
from asset_helper import (
    ASSETS,
    get_image_base64,
    get_event_poster_path,
    get_user_avatar_html,
    render_html,
    clean_html
)


def render_organizer_dashboard():
    """Render the full Event Coordinator interface."""
    user = get_current_user()
    if not user or user.get("role") not in ["organizer", "admin"]:
        st.error("Access Restricted: Only authorized Event Organizers and Administrators can access this portal.")
        return

    logo_b64 = get_image_base64(ASSETS["logo_college"])
    avatar_html = get_user_avatar_html(user, size=48)

    # ---------------- HEADER WITH PROFILE AVATAR ----------------
    render_html(
        f'<div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">'
        f'<div style="display: flex; align-items: center; gap: 12px;">'
        f'<img src="{logo_b64}" style="height: 44px; width: auto;" alt="SIMATS"/>'
        f'<div>'
        f'<h2 style="margin: 0; color: #0A2540; font-size: 1.4rem;">Event Coordinator Management Portal</h2>'
        f'<p style="margin: 2px 0 0 0; color: #64748B; font-size: 0.85rem;">Coordinator: <strong>{user["full_name"]}</strong> &nbsp;|&nbsp; {user.get("department") or "SIMATS Faculty/Staff"}</p>'
        f'</div>'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 12px;">'
        f'<span class="simats-badge badge-internal" style="font-size: 0.78rem;">Authorized Event Coordinator</span>'
        f'{avatar_html}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # ---------------- ORGANIZER KPIS ----------------
    my_events = execute_query("SELECT * FROM events WHERE organizer_id = ? ORDER BY created_at DESC", (user["id"],))
    total_events = len(my_events)

    kpi_query = """
    SELECT 
        COUNT(DISTINCT r.id) as total_registrations,
        COUNT(DISTINCT a.id) as total_attendance,
        COALESCE(SUM(p.amount), 0.0) as total_revenue
    FROM events e
    LEFT JOIN registrations r ON e.id = r.event_id AND r.status != 'Cancelled'
    LEFT JOIN attendance a ON r.id = a.registration_id AND a.status = 'Present'
    LEFT JOIN payments p ON r.id = p.registration_id AND p.status = 'Success'
    WHERE e.organizer_id = ?
    """
    kpis = execute_query_one(kpi_query, (user["id"],)) or {"total_registrations": 0, "total_attendance": 0, "total_revenue": 0.0}

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(textwrap.dedent(f"""
        <div class="simats-metric-box">
            <div class="simats-metric-label">Events Created</div>
            <div class="simats-metric-value">{total_events}</div>
        </div>
        """).strip(), unsafe_allow_html=True)
    with col_m2:
        st.markdown(textwrap.dedent(f"""
        <div class="simats-metric-box green">
            <div class="simats-metric-label">Total Registrations</div>
            <div class="simats-metric-value">{kpis['total_registrations']}</div>
        </div>
        """).strip(), unsafe_allow_html=True)
    with col_m3:
        st.markdown(textwrap.dedent(f"""
        <div class="simats-metric-box gold">
            <div class="simats-metric-label">Checked-In Attendees</div>
            <div class="simats-metric-value">{kpis['total_attendance']}</div>
        </div>
        """).strip(), unsafe_allow_html=True)
    with col_m4:
        st.markdown(textwrap.dedent(f"""
        <div class="simats-metric-box">
            <div class="simats-metric-label">Simulated Collections</div>
            <div class="simats-metric-value">₹{int(kpis['total_revenue'])}</div>
        </div>
        """).strip(), unsafe_allow_html=True)

    st.write("")

    tabs = st.tabs([
        "📋 My Events & State Machine",
        "➕ Create New Event",
        "👥 Participant Management & CSV Export",
        "📷 QR Attendance Scanner Station",
        "⚙️ Coordinator Profile Settings"
    ])

    # ---------------- TAB 1: MY EVENTS & LIFECYCLE ----------------
    with tabs[0]:
        st.markdown("### Manage Organized Events")
        
        if not my_events:
            st.info("You haven't created any events yet. Use the 'Create New Event' tab to draft your first proposal.")
        else:
            for ev in my_events:
                eff_status = get_effective_status(ev)
                
                # Fetch participant counts
                counts = execute_query_one("""
                SELECT 
                    COUNT(r.id) as reg_count,
                    COUNT(a.id) as att_count
                FROM registrations r
                LEFT JOIN attendance a ON r.id = a.registration_id AND a.status = 'Present'
                WHERE r.event_id = ? AND r.status != 'Cancelled'
                """, (ev["id"],)) or {"reg_count": 0, "att_count": 0}

                cur_poster_path = get_event_poster_path(ev)
                cur_poster_b64 = get_image_base64(cur_poster_path)

                with st.container():
                    # HTML-safe event card with thumbnail and metadata
                    card_html = textwrap.dedent(f"""
                    <div class="simats-card" style="margin-bottom: 0.6rem; padding: 14px 18px; border-radius: 10px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 2px 8px rgba(10,37,64,0.04);">
                        <div style="display: flex; gap: 18px; align-items: center; flex-wrap: wrap;">
                            <div style="flex: 0 0 140px; max-width: 140px; border-radius: 8px; overflow: hidden; border: 1px solid #CBD5E1; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">
                                <img src="{cur_poster_b64}" style="width: 100%; height: 105px; object-fit: cover; display: block;" alt="{ev['title']} Poster"/>
                            </div>
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                    <span class="simats-badge badge-internal">{ev['category']}</span>
                                    <span class="simats-badge badge-external">{ev['format']}</span>
                                    <span class="simats-badge badge-status-open">Status: {ev['status']}</span>
                                    {f'<span class="simats-badge badge-status-pending">Live: {eff_status}</span>' if eff_status != ev['status'] else ''}
                                </div>
                                <h3 style="margin: 0 0 6px 0; color: #0A2540; font-size: 1.2rem; font-weight: 700;">{ev['title']}</h3>
                                <p style="margin: 0 0 8px 0; color: #64748B; font-size: 0.88rem; line-height: 1.35;">{ev['summary'] or (ev['description'][:120] + '...')}</p>
                                <div style="display: flex; gap: 16px; font-size: 0.82rem; color: #475569; flex-wrap: wrap;">
                                    <div>📅 <strong>Dates:</strong> {ev['start_time'][:16]} to {ev['end_time'][:16]}</div>
                                    <div>📍 <strong>Venue:</strong> {ev['venue']}</div>
                                    <div>👥 <strong>Capacity:</strong> {counts['reg_count']}/{ev['capacity']} (Attended: {counts['att_count']})</div>
                                    <div>💳 <strong>Ext Fee:</strong> ₹{int(ev['external_fee'])} | <strong>Internal:</strong> ₹0.00</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """).strip()
                    st.html(card_html)

                    # Show Admin Feedback if present
                    if ev.get("admin_feedback"):
                        st.caption(f"**Administrator Feedback:** {ev['admin_feedback']}")

                    # State Machine Action Buttons
                    col_act1, col_act2, col_act3, col_act4 = st.columns(4)

                    # 1. Submit for Approval or Publish
                    with col_act1:
                        if ev["status"] in ["Draft", "Rejected"]:
                            if st.button("📤 Submit for Approval", key=f"btn_sub_{ev['id']}", type="primary", use_container_width=True):
                                ok, msg = submit_draft_for_approval(ev["id"], user["id"])
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        elif ev["status"] == "Approved":
                            if st.button("🚀 Publish Event", key=f"btn_pub_{ev['id']}", type="primary", use_container_width=True):
                                ok, msg = publish_event(user["id"], ev["id"])
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                    # 2. Transition to Ongoing
                    with col_act2:
                        if ev["status"] in ["Approved", "Published", "Registration Open", "Registration Closed", "Full"]:
                            if st.button("▶️ Mark as Ongoing", key=f"btn_ong_{ev['id']}", use_container_width=True):
                                ok, msg = set_event_status(user["id"], ev["id"], "Ongoing")
                                if ok:
                                    st.success(msg)
                                    st.rerun()

                    # 3. Mark as Completed (Unlocks Certificates!)
                    with col_act3:
                        if ev["status"] == "Ongoing":
                            if st.button("🏁 Mark as Completed", key=f"btn_comp_{ev['id']}", type="primary", use_container_width=True):
                                ok, msg = set_event_status(user["id"], ev["id"], "Completed")
                                if ok:
                                    st.success(msg)
                                    st.rerun()

                    # 4. Cancel Event
                    with col_act4:
                        if ev["status"] not in ["Completed", "Cancelled"]:
                            if st.button("🛑 Cancel Event", key=f"btn_canc_{ev['id']}", use_container_width=True):
                                ok, msg = set_event_status(user["id"], ev["id"], "Cancelled")
                                if ok:
                                    st.warning(msg)
                                    st.rerun()

                    # Material Changes Edit Expander
                    with st.expander(f"✏️ Edit Event Details (Event #{ev['id']})"):
                        st.info("⚠️ **Business Rule:** Material changes to dates, venue, format, fees, or capacity reduction on an Approved or Published event will immediately revert the event to **'Pending Approval'** for re-approval by Administrators.")
                        
                        with st.form(f"edit_event_form_{ev['id']}"):
                            ed_title = st.text_input("Event Title", value=ev["title"])
                            ed_summary = st.text_input("Summary", value=ev["summary"] or "")
                            ed_desc = st.text_area("Full Description", value=ev["description"])

                            # Custom Event Poster Preview and File Uploader
                            poster_preview_html = textwrap.dedent(f"""
                            <div style="margin-bottom: 8px;">
                                <span style="font-size: 0.85rem; font-weight: 600; color: #475569;">Active Event Poster:</span><br/>
                                <img src="{cur_poster_b64}" style="height: 110px; border-radius: 6px; border: 1px solid #CBD5E1; margin-top: 4px; object-fit: cover;" alt="Poster preview"/>
                            </div>
                            """).strip()
                            st.markdown(poster_preview_html, unsafe_allow_html=True)

                            edit_poster_file = st.file_uploader(
                                "Replace Event Poster (PNG/JPG)",
                                type=["png", "jpg", "jpeg"],
                                key=f"uploader_edit_event_poster_{ev['id']}",
                                help="Upload a new custom poster from your local drive. Leave empty to keep the current poster."
                            )
                            
                            c_cat, c_fmt = st.columns(2)
                            with c_cat:
                                cat_idx = EVENT_CATEGORIES.index(ev["category"]) if ev["category"] in EVENT_CATEGORIES else 0
                                ed_category = st.selectbox("Category", EVENT_CATEGORIES, index=cat_idx)
                            with c_fmt:
                                fmt_idx = EVENT_FORMATS.index(ev["format"]) if ev["format"] in EVENT_FORMATS else 0
                                ed_format = st.selectbox("Format", EVENT_FORMATS, index=fmt_idx)

                            ed_venue = st.text_input("Venue / Link", value=ev["venue"])

                            c_st, c_et = st.columns(2)
                            with c_st:
                                ed_start = st.text_input("Event Start (YYYY-MM-DD HH:MM:SS)", value=ev["start_time"])
                            with c_et:
                                ed_end = st.text_input("Event End (YYYY-MM-DD HH:MM:SS)", value=ev["end_time"])

                            c_rs, c_re = st.columns(2)
                            with c_rs:
                                ed_reg_s = st.text_input("Reg Start (YYYY-MM-DD HH:MM:SS)", value=ev["reg_start"])
                            with c_re:
                                ed_reg_e = st.text_input("Reg End (YYYY-MM-DD HH:MM:SS)", value=ev["reg_end"])

                            c_cap, c_fee = st.columns(2)
                            with c_cap:
                                ed_cap = st.number_input("Capacity", value=int(ev["capacity"]), min_value=1)
                            with c_fee:
                                ed_fee = st.number_input("External Participant Fee (₹)", value=float(ev["external_fee"]), min_value=0.0, step=10.0)

                            ed_agenda = st.text_area("Agenda", value=ev.get("agenda") or "")
                            ed_sig_n = st.text_input("Signatory Name", value=ev.get("signatory_name") or "")
                            ed_sig_t = st.text_input("Signatory Title", value=ev.get("signatory_title") or "")

                            submit_edit = st.form_submit_button("Save Changes", type="primary")
                            if submit_edit:
                                ed_banner = ev.get("banner_url") or "assets/event_posters/Poster Template.png"
                                if edit_poster_file is not None:
                                    posters_dir = os.path.join(STATIC_DIR, "posters")
                                    os.makedirs(posters_dir, exist_ok=True)
                                    safe_name = f"poster_ev{ev['id']}_{int(datetime.datetime.now().timestamp())}_{edit_poster_file.name.replace(' ', '_')}"
                                    poster_abs_path = os.path.join(posters_dir, safe_name)
                                    with open(poster_abs_path, "wb") as pf:
                                        pf.write(edit_poster_file.getbuffer())
                                    ed_banner = f"static/posters/{safe_name}"

                                ok, msg = update_event(
                                    event_id=ev["id"],
                                    actor_id=user["id"],
                                    actor_role=user["role"],
                                    title=ed_title,
                                    summary=ed_summary,
                                    description=ed_desc,
                                    banner_url=ed_banner,
                                    category=ed_category,
                                    format_type=ed_format,
                                    venue=ed_venue,
                                    start_time=ed_start,
                                    end_time=ed_end,
                                    reg_start=ed_reg_s,
                                    reg_end=ed_reg_e,
                                    capacity=ed_cap,
                                    external_fee=ed_fee,
                                    agenda=ed_agenda,
                                    signatory_name=ed_sig_n,
                                    signatory_title=ed_sig_t
                                )
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    st.divider()

    # ---------------- TAB 2: CREATE NEW EVENT ----------------
    with tabs[1]:
        st.markdown("### Propose a New University Event")
        st.caption("Organizers submit new proposals for Administrator review before they appear on the public portal.")

        with st.form("create_new_event_form"):
            c_t, c_cat = st.columns([3, 1])
            with c_t:
                new_title = st.text_input("Event Title *", placeholder="e.g. National Symposium on Bio-Computing 2026")
            with c_cat:
                new_category = st.selectbox("Category *", EVENT_CATEGORIES)

            new_summary = st.text_input("Short Summary *", placeholder="One-sentence tagline describing the event")
            new_desc = st.text_area("Full Description *", placeholder="Provide in-depth overview, learning objectives, and criteria...")
            new_poster_file = st.file_uploader(
                "Upload Custom Event Poster (PNG/JPG)",
                type=["png", "jpg", "jpeg"],
                key="uploader_new_event_poster",
                help="Upload an official high-resolution custom event poster graphic from your local drive."
            )

            c_fmt, c_ven = st.columns([1, 2])
            with c_fmt:
                new_format = st.selectbox("Event Format *", EVENT_FORMATS)
            with c_ven:
                new_venue = st.text_input("Venue / Link *", placeholder="e.g. Main Auditorium, SIMATS Campus, Chennai")

            now = datetime.datetime.now()
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                new_start_dt = st.text_input("Event Start Date/Time *", value=(now + datetime.timedelta(days=14, hours=9)).strftime("%Y-%m-%d %H:%M:%S"))
                new_reg_s = st.text_input("Registration Opens *", value=now.strftime("%Y-%m-%d %H:%M:%S"))
            with c_d2:
                new_end_dt = st.text_input("Event End Date/Time *", value=(now + datetime.timedelta(days=15, hours=17)).strftime("%Y-%m-%d %H:%M:%S"))
                new_reg_e = st.text_input("Registration Closes *", value=(now + datetime.timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S"))

            c_cap, c_ifee, c_efee = st.columns(3)
            with c_cap:
                new_capacity = st.number_input("Max Capacity (Seats) *", value=100, min_value=5, step=10)
            with c_ifee:
                st.text_input("Internal SIMATS Fee (₹)", value="0.00 (Locked by Policy)", disabled=True)
            with c_efee:
                new_ext_fee = st.number_input("External Participant Fee (₹)", value=250.0, min_value=0.0, step=25.0)

            new_agenda = st.text_area("Event Schedule / Agenda", placeholder="Day 1: Inauguration, Keynote\nDay 2: Technical Sessions, Valedictory")

            st.markdown("##### Certificate Signatory Authority")
            c_sig1, c_sig2 = st.columns(2)
            with c_sig1:
                new_sig_name = st.text_input("Signatory Full Name", value=user["full_name"])
            with c_sig2:
                new_sig_title = st.text_input("Signatory Designation", value=f"Convener, {user.get('department') or 'SIMATS'}")

            st.write("")
            col_save_draft, col_sub_admin = st.columns(2)
            with col_save_draft:
                btn_draft = st.form_submit_button("💾 Save Proposal as Draft", use_container_width=True)
            with col_sub_admin:
                btn_submit = st.form_submit_button("🚀 Submit to Administrator for Review", type="primary", use_container_width=True)

            if btn_draft or btn_submit:
                new_banner = "assets/event_posters/Poster Template.png"
                if new_poster_file is not None:
                    posters_dir = os.path.join(STATIC_DIR, "posters")
                    os.makedirs(posters_dir, exist_ok=True)
                    safe_name = f"poster_new_{int(datetime.datetime.now().timestamp())}_{new_poster_file.name.replace(' ', '_')}"
                    poster_abs_path = os.path.join(posters_dir, safe_name)
                    with open(poster_abs_path, "wb") as pf:
                        pf.write(new_poster_file.getbuffer())
                    new_banner = f"static/posters/{safe_name}"

                submit_flag = bool(btn_submit)
                ok, msg, eid = create_event(
                    organizer_id=user["id"],
                    title=new_title,
                    summary=new_summary,
                    description=new_desc,
                    banner_url=new_banner,
                    category=new_category,
                    format_type=new_format,
                    venue=new_venue,
                    start_time=new_start_dt,
                    end_time=new_end_dt,
                    reg_start=new_reg_s,
                    reg_end=new_reg_e,
                    capacity=new_capacity,
                    external_fee=new_ext_fee,
                    agenda=new_agenda,
                    signatory_name=new_sig_name,
                    signatory_title=new_sig_title,
                    submit_for_approval=submit_flag
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ---------------- TAB 3: PARTICIPANT MANAGEMENT & CSV EXPORT ----------------
    with tabs[2]:
        st.markdown("### Participant Roster & Attendance Tracking")
        
        if not my_events:
            st.info("No events found.")
        else:
            event_options = {f"{ev['title']} (#{ev['id']})": ev["id"] for ev in my_events}
            sel_event_title = st.selectbox("Select Event to Inspect", list(event_options.keys()))
            sel_event_id = event_options[sel_event_title]

            # Fetch participants
            roster_sql = """
            SELECT 
                r.registration_id,
                u.full_name as participant_name,
                u.email as participant_email,
                u.phone as contact_number,
                u.category as classification,
                u.institution,
                u.department,
                r.payment_status,
                r.created_at as registered_at,
                COALESCE(a.status, 'Absent / Not Scanned') as attendance_status,
                a.scanned_at,
                p.transaction_id,
                p.amount as fee_paid
            FROM registrations r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN attendance a ON r.id = a.registration_id
            LEFT JOIN payments p ON r.id = p.registration_id AND p.status = 'Success'
            WHERE r.event_id = ? AND r.status != 'Cancelled'
            ORDER BY r.created_at ASC
            """
            roster = execute_query(roster_sql, (sel_event_id,))

            if not roster:
                st.info("No registrations yet for this event.")
            else:
                df = pd.DataFrame(roster)
                
                # Filter row
                c_f1, c_f2 = st.columns([2, 1])
                with c_f1:
                    filter_att = st.radio("Filter Attendance", ["All", "Present", "Absent / Not Scanned"], horizontal=True)
                with c_f2:
                    # CSV Export button
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Roster (CSV)",
                        data=csv_data,
                        file_name=f"Roster_{sel_event_title[:20].replace(' ', '_')}.csv",
                        mime="text/csv",
                        key="btn_dl_roster_csv",
                        use_container_width=True
                    )

                if filter_att != "All":
                    filtered_df = df[df["attendance_status"] == filter_att]
                else:
                    filtered_df = df

                st.write(f"Showing **{len(filtered_df)}** participants:")
                st.dataframe(filtered_df, use_container_width=True)

    # ---------------- TAB 4: QR ATTENDANCE SCANNER ----------------
    with tabs[3]:
        st.markdown("### Dual-Mode Attendance Check-In Station")
        st.caption("Scan attendees' official QR code tickets or use manual Registration ID lookup. Duplicate check-ins are strictly prevented.")

        if not my_events:
            st.info("No organized events found.")
        else:
            scan_event_options = {f"{ev['title']} (#{ev['id']})": ev["id"] for ev in my_events}
            scan_event_choice = st.selectbox("Select Active Event for Check-In Verification", list(scan_event_options.keys()))
            target_event_id = scan_event_options[scan_event_choice]

            scan_mode = st.radio("Choose Verification Mode", ["📷 Camera Scanner (Live QR)", "⌨️ Manual Registration ID Lookup"], horizontal=True)

            if scan_mode == "📷 Camera Scanner (Live QR)":
                st.markdown("##### Point Attendee Ticket QR at Camera")
                camera_img = st.camera_input("Capture Ticket QR Code")
                if camera_img is not None:
                    bytes_data = camera_img.getvalue()
                    decoded_payload = decode_qr_image(bytes_data)

                    if decoded_payload:
                        st.info(f"Decoded Code: `{decoded_payload}`")
                        ok, msg, details = verify_and_check_in(decoded_payload, target_event_id, user["id"])
                        if ok:
                            st.success(f"🎉 **{msg}**")
                            st.json(details)
                        else:
                            st.error(f"❌ {msg}")
                            if details:
                                st.warning(f"Prior Attendee Record: {details.get('full_name')} ({details.get('category')})")
                    else:
                        st.warning("⚠️ Could not detect a valid QR code in the captured frame. Please hold the ticket closer and steady, or use Manual Lookup below.")

            else:
                st.markdown("##### Manual Registration ID Lookup Fallback")
                with st.form("manual_checkin_form"):
                    manual_reg_id = st.text_input("Enter Participant Registration ID", placeholder="e.g. SIMATS-REG-2026-001")
                    submit_manual = st.form_submit_button("Verify & Check-In Attendee", type="primary")

                    if submit_manual:
                        if not manual_reg_id.strip():
                            st.error("Please enter a Registration ID.")
                        else:
                            ok, msg, details = verify_and_check_in(manual_reg_id.strip(), target_event_id, user["id"])
                            if ok:
                                st.success(f"🎉 **{msg}**")
                                st.json({
                                    "Registration ID": details["registration_id"],
                                    "Attendee Name": details["full_name"],
                                    "Category": details["category"],
                                    "Institution": details["institution"],
                                    "Department": details["department"]
                                })
                            else:
                                st.error(f"❌ {msg}")
                                if details:
                                    st.warning(f"Attendee Info: {details.get('full_name')} ({details.get('category')})")

    # ---------------- TAB 5: COORDINATOR PROFILE SETTINGS ----------------
    with tabs[4]:
        st.markdown("### Coordinator Profile & Account Settings")
        st.caption("Manage your official department information and upload a personalized profile photo displayed across portals.")

        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            render_html(
                f'<div style="text-align: center; padding: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; margin-bottom: 12px;">'
                f'<div style="margin-bottom: 8px;">{get_user_avatar_html(user, size=84)}</div>'
                f'<div style="font-weight: 700; color: #0A2540; font-size: 1.05rem;">{user["full_name"]}</div>'
                f'<div style="font-size: 0.8rem; color: #64748B;">{user["email"]}</div>'
                f'<div style="margin-top: 6px;"><span class="simats-badge badge-internal" style="font-size: 0.72rem;">Event Coordinator</span></div>'
                f'</div>'
            )

        with col_p2:
            with st.form("coordinator_profile_form"):
                coord_name = st.text_input("Full Name", value=user["full_name"])
                coord_phone = st.text_input("Contact Phone Number", value=user.get("phone") or "")
                coord_dept = st.text_input("Department / Academic Unit", value=user.get("department") or "")
                
                coord_avatar_file = st.file_uploader(
                    "Upload / Replace Profile Photo (PNG/JPG)",
                    type=["png", "jpg", "jpeg"],
                    key="uploader_coord_avatar",
                    help="Upload a professional profile photo. Files are securely stored locally."
                )

                submit_coord_prof = st.form_submit_button("💾 Save Profile Changes", type="primary")
                if submit_coord_prof:
                    new_avatar_rel = user.get("avatar_url")
                    if coord_avatar_file is not None:
                        os.makedirs(AVATARS_DIR, exist_ok=True)
                        avatar_filename = f"avatar_user_{user['id']}_{int(datetime.datetime.now().timestamp())}_{coord_avatar_file.name.replace(' ', '_')}"
                        avatar_abs_path = os.path.join(AVATARS_DIR, avatar_filename)
                        with open(avatar_abs_path, "wb") as af:
                            af.write(coord_avatar_file.getbuffer())
                        new_avatar_rel = f"static/avatars/{avatar_filename}"

                    ok, msg = update_user_profile(
                        user_id=user["id"],
                        full_name=coord_name,
                        phone=coord_phone,
                        institution=user.get("institution") or "SIMATS",
                        department=coord_dept,
                        avatar_url=new_avatar_rel
                    )
                    if ok:
                        st.success("✅ " + msg)
                        refreshed = execute_query_one("SELECT * FROM users WHERE id = ?", (user["id"],))
                        st.session_state["user"] = dict(refreshed)
                        st.rerun()
                    else:
                        st.error("❌ " + msg)
