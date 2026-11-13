"""
SIMATS Event Sphere - Administrator Dashboard View Module
Provides system overview metrics, event approval queue with actionable feedback,
exclusive organizer account provisioning, platform financial ledger & refunds,
immutable audit log inspection, and admin profile settings with avatar photo upload.
"""

import os
import textwrap
import datetime
import streamlit as st
import pandas as pd
from database import (
    execute_query,
    execute_query_one,
    execute_write,
    STATIC_DIR,
    AVATARS_DIR
)
from auth import get_current_user, create_organizer_by_admin, update_user_profile
from event_service import admin_review_event
from payment_service import refund_payment
from asset_helper import (
    ASSETS,
    get_image_base64,
    get_event_poster_path,
    get_user_avatar_html,
    render_html,
    clean_html
)


def render_admin_dashboard():
    """Render the full Administrator management interface."""
    user = get_current_user()
    if not user or user.get("role") != "admin":
        st.error("Access Denied: Administrator clearance is required.")
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
        f'<h2 style="margin: 0; color: #0A2540; font-size: 1.4rem;">SIMATS Central Administration Console</h2>'
        f'<p style="margin: 2px 0 0 0; color: #64748B; font-size: 0.85rem;">Administrator: <strong>{user["full_name"]}</strong> &nbsp;|&nbsp; Academic &amp; Event Governance Oversight</p>'
        f'</div>'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 12px;">'
        f'<span class="simats-badge badge-internal" style="background: #FEF3C7; color: #92400E; border-color: #FCD34D; font-size: 0.78rem;">👑 Platform Super-Admin</span>'
        f'{avatar_html}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # ---------------- GLOBAL PLATFORM KPIS ----------------
    users_stats = execute_query_one("""
    SELECT 
        COUNT(*) as total_users,
        SUM(CASE WHEN role = 'student' AND category = 'internal_verified' THEN 1 ELSE 0 END) as internal_count,
        SUM(CASE WHEN role = 'student' AND category = 'external' THEN 1 ELSE 0 END) as external_count,
        SUM(CASE WHEN role = 'organizer' THEN 1 ELSE 0 END) as organizer_count
    FROM users
    """) or {}

    events_stats = execute_query_one("""
    SELECT 
        COUNT(*) as total_events,
        SUM(CASE WHEN status = 'Pending Approval' THEN 1 ELSE 0 END) as pending_approval_count,
        SUM(CASE WHEN status IN ('Approved', 'Published', 'Ongoing') THEN 1 ELSE 0 END) as active_events_count
    FROM events
    """) or {}

    financial_stats = execute_query_one("""
    SELECT 
        COALESCE(SUM(CASE WHEN status = 'Success' THEN amount ELSE 0 END), 0.0) as gross_collections,
        COALESCE(SUM(CASE WHEN status = 'Refunded' THEN amount ELSE 0 END), 0.0) as total_refunds,
        COUNT(CASE WHEN status = 'Success' THEN 1 END) as successful_txns
    FROM payments
    """) or {}

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_html(
            f'<div class="simats-metric-box">'
            f'<div class="simats-metric-label">Total Platform Users</div>'
            f'<div class="simats-metric-value">{users_stats.get("total_users", 0)}</div>'
            f'<div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">'
            f'Internal: {users_stats.get("internal_count", 0)} | Ext: {users_stats.get("external_count", 0)}'
            f'</div>'
            f'</div>'
        )

    with col_m2:
        pending_cnt = events_stats.get('pending_approval_count', 0)
        border_class = "gold" if pending_cnt > 0 else ""
        render_html(
            f'<div class="simats-metric-box {border_class}">'
            f'<div class="simats-metric-label">Pending Event Approvals</div>'
            f'<div class="simats-metric-value" style="color: {"#D97706" if pending_cnt > 0 else "#0A2540"};">'
            f'{pending_cnt}'
            f'</div>'
            f'<div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">'
            f'Total Events: {events_stats.get("total_events", 0)} (Active: {events_stats.get("active_events_count", 0)})'
            f'</div>'
            f'</div>'
        )

    with col_m3:
        render_html(
            f'<div class="simats-metric-box green">'
            f'<div class="simats-metric-label">Simulated Gross Collections</div>'
            f'<div class="simats-metric-value">₹{int(financial_stats.get("gross_collections", 0))}</div>'
            f'<div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">'
            f'Successful Transactions: {financial_stats.get("successful_txns", 0)}'
            f'</div>'
            f'</div>'
        )

    with col_m4:
        render_html(
            f'<div class="simats-metric-box">'
            f'<div class="simats-metric-label">Refunds Processed</div>'
            f'<div class="simats-metric-value">₹{int(financial_stats.get("total_refunds", 0))}</div>'
            f'<div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">'
            f'Total Organizers: {users_stats.get("organizer_count", 0)}'
            f'</div>'
            f'</div>'
        )

    st.write("")

    tabs = st.tabs([
        "📥 Event Approval Queue",
        "👥 User & Organizer Management",
        "💳 Financial Ledger & Refunds",
        "🛡️ Platform Audit Logs",
        "📊 Reports & Analytics",
        "⚙️ Admin Profile Settings"
    ])

    # ---------------- TAB 1: EVENT APPROVAL QUEUE ----------------
    with tabs[0]:
        st.markdown("### Events Awaiting Administrator Approval")
        
        pending_events = execute_query("""
        SELECT e.*, u.full_name as organizer_name, u.email as organizer_email, u.department as organizer_department
        FROM events e
        JOIN users u ON e.organizer_id = u.id
        WHERE e.status = 'Pending Approval'
        ORDER BY e.updated_at ASC
        """)

        if not pending_events:
            st.success("✅ **Queue Clear:** No events are currently pending approval.")
        else:
            st.warning(f"There are **{len(pending_events)}** event proposals awaiting administrative review:")
            
            for ev in pending_events:
                ev_poster = get_event_poster_path(ev)
                ev_poster_b64 = get_image_base64(ev_poster)

                with st.container():
                    agenda_html = f'<div style="margin-top: 6px; font-size: 0.82rem; color: #334155;"><strong>Agenda:</strong> {ev["agenda"]}</div>' if ev.get("agenda") else ''
                    ev_summary = ev['summary'] or (ev['description'][:120] + '...')
                    render_html(
                        f'<div class="simats-card" style="margin-bottom: 0.6rem; padding: 14px 18px; border-radius: 10px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 2px 8px rgba(10,37,64,0.04);">'
                        f'<div style="display: flex; gap: 18px; align-items: center; flex-wrap: wrap;">'
                        f'<div style="flex: 0 0 140px; max-width: 140px; border-radius: 8px; overflow: hidden; border: 1px solid #CBD5E1; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">'
                        f'<img src="{ev_poster_b64}" style="width: 100%; height: 105px; object-fit: cover; display: block;" alt="{ev["title"]} Poster"/>'
                        f'</div>'
                        f'<div style="flex: 1; min-width: 280px;">'
                        f'<div style="display: flex; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">'
                        f'<span class="simats-badge badge-internal">{ev["category"]}</span>'
                        f'<span class="simats-badge badge-external">{ev["format"]}</span>'
                        f'<span class="simats-badge badge-status-pending">Pending Approval</span>'
                        f'</div>'
                        f'<h3 style="margin: 0 0 6px 0; color: #0A2540; font-size: 1.2rem; font-weight: 700;">{ev["title"]}</h3>'
                        f'<p style="margin: 0 0 8px 0; color: #475569; font-size: 0.88rem; line-height: 1.35;">{ev_summary}</p>'
                        f'<div style="display: flex; gap: 16px; font-size: 0.82rem; color: #64748B; flex-wrap: wrap;">'
                        f'<div>👤 <strong>Organizer:</strong> {ev["organizer_name"]} ({ev.get("organizer_department") or "Faculty"})</div>'
                        f'<div>📅 <strong>Dates:</strong> {ev["start_time"][:16]} to {ev["end_time"][:16]}</div>'
                        f'<div>📍 <strong>Venue:</strong> {ev["venue"]}</div>'
                        f'<div>👥 <strong>Capacity:</strong> {ev["capacity"]} seats</div>'
                        f'<div>💳 <strong>Ext Fee:</strong> ₹{int(ev["external_fee"])} | <strong>Internal:</strong> ₹0.00</div>'
                        f'</div>'
                        f'{agenda_html}'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )

                    with st.form(f"admin_review_form_{ev['id']}"):
                        feedback_input = st.text_input("Reviewer Comments / Instructions (Mandatory for rejections)", placeholder="e.g. Approved by Academic Committee OR Please adjust schedule to avoid exam week.")
                        c_app, c_rej = st.columns(2)
                        with c_app:
                            btn_app = st.form_submit_button("✅ Approve Event Proposal", type="primary", use_container_width=True)
                        with c_rej:
                            btn_rej = st.form_submit_button("❌ Reject Event Proposal", use_container_width=True)

                        if btn_app:
                            ok, msg = admin_review_event(user["id"], ev["id"], "Approve", feedback_input)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                        if btn_rej:
                            ok, msg = admin_review_event(user["id"], ev["id"], "Reject", feedback_input)
                            if ok:
                                st.warning(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    st.divider()

    # ---------------- TAB 2: USER & ORGANIZER MANAGEMENT ----------------
    with tabs[1]:
        st.markdown("### Authorized Organizer Provisioning & User Directory")
        st.info("ℹ️ **Security Rule:** Event Organizer accounts cannot self-register. They are created and authorized strictly by Administrators.")

        with st.expander("➕ Provision / Authorize New Event Organizer", expanded=False):
            with st.form("create_organizer_form"):
                c_o1, c_o2 = st.columns(2)
                with c_o1:
                    org_email = st.text_input("Organizer Institutional Email *", placeholder="e.g. prof.name@simats.edu")
                    org_name = st.text_input("Faculty / Organizer Full Name *", placeholder="e.g. Dr. K. Ramanathan")
                    org_phone = st.text_input("Phone Number", placeholder="+91 98765 43210")
                with c_o2:
                    org_pwd = st.text_input("Initial Temporary Password *", type="password", value="Organizer@123")
                    org_dept = st.text_input("Academic Department *", placeholder="e.g. Computer Science & Engineering")
                    org_inst = st.text_input("Institution", value="SIMATS Deemed University", disabled=True)

                submit_org = st.form_submit_button("Authorise & Create Organizer Account", type="primary", use_container_width=True)
                if submit_org:
                    if not org_email or not org_pwd or not org_name or not org_dept:
                        st.error("Email, password, full name, and department are mandatory.")
                    else:
                        ok, msg = create_organizer_by_admin(
                            admin_id=user["id"],
                            email=org_email,
                            password=org_pwd,
                            full_name=org_name,
                            phone=org_phone,
                            institution=org_inst,
                            department=org_dept
                        )
                        if ok:
                            st.success(f"🎉 {msg}")
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("##### Registered User Directory")
        col_f_role, col_f_search = st.columns([1, 2])
        with col_f_role:
            role_sel = st.selectbox("Filter Role", ["All", "student", "organizer", "admin"])
        with col_f_search:
            search_user = st.text_input("Search Name / Email", placeholder="Filter users...")

        query = "SELECT id, full_name, email, role, category, institution, department, created_at FROM users WHERE 1=1"
        params = []
        if role_sel != "All":
            query += " AND role = ?"
            params.append(role_sel)
        if search_user.strip():
            query += " AND (full_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search_user}%", f"%{search_user}%"])
        query += " ORDER BY created_at DESC"

        users_list = execute_query(query, tuple(params))
        df_users = pd.DataFrame(users_list)
        st.write(f"Showing **{len(df_users)}** users:")
        st.dataframe(df_users, use_container_width=True)

    # ---------------- TAB 3: FINANCIAL LEDGER & REFUNDS ----------------
    with tabs[2]:
        st.markdown("### Simulated Payment Ledger & Financial Audit")
        
        payments = execute_query("""
        SELECT 
            p.id as payment_id,
            p.transaction_id,
            r.registration_id,
            u.full_name as participant_name,
            u.email as participant_email,
            e.title as event_title,
            p.amount,
            p.payment_method,
            p.status as payment_status,
            p.created_at as txn_time
        FROM payments p
        JOIN registrations r ON p.registration_id = r.id
        JOIN users u ON r.user_id = u.id
        JOIN events e ON r.event_id = e.id
        ORDER BY p.created_at DESC
        """)

        if payments:
            df_pay = pd.DataFrame(payments)
            st.dataframe(df_pay, use_container_width=True)

            st.markdown("##### Process Simulated Refund")
            refundable_options = {
                f"{p['transaction_id']} - {p['participant_name']} (₹{p['amount']})": p["payment_id"]
                for p in payments if p["payment_status"] == "Success" and p["amount"] > 0
            }

            if refundable_options:
                col_r1, col_r2 = st.columns([2, 1])
                with col_r1:
                    sel_refund_label = st.selectbox("Select Transaction to Refund", list(refundable_options.keys()))
                    refund_pid = refundable_options[sel_refund_label]
                    refund_reason = st.text_input("Refund Reason", placeholder="e.g. Accidental duplicate payment")
                with col_r2:
                    st.write("")
                    st.write("")
                    if st.button("Simulate Refund Execution", type="primary", use_container_width=True):
                        ok, msg = refund_payment(user["id"], refund_pid, refund_reason)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.caption("No eligible refundable paid transactions currently on record.")
        else:
            st.info("No payment transactions recorded on platform.")

    # ---------------- TAB 4: PLATFORM AUDIT LOGS ----------------
    with tabs[3]:
        st.markdown("### Immutable Platform Audit Logs")
        st.caption("Complete chronological record of all system events, role changes, state transitions, and transactions for strict accountability.")

        audit_logs = execute_query("""
        SELECT 
            a.id,
            a.timestamp,
            COALESCE(u.email, 'SYSTEM') as actor_email,
            COALESCE(u.role, 'SYSTEM') as actor_role,
            a.action,
            a.target_table,
            a.target_id,
            a.details
        FROM audit_logs a
        LEFT JOIN users u ON a.actor_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT 100
        """)

        if audit_logs:
            df_audit = pd.DataFrame(audit_logs)
            st.dataframe(df_audit, use_container_width=True)
        else:
            st.write("No audit logs available.")

    # ---------------- TAB 5: REPORTS & ANALYTICS ----------------
    with tabs[4]:
        st.markdown("### Platform Analytics & Category Breakdown")
        
        cat_stats = execute_query("""
        SELECT 
            category,
            COUNT(*) as event_count,
            COALESCE(SUM(capacity), 0) as total_seats,
            COALESCE(AVG(external_fee), 0.0) as avg_external_fee
        FROM events
        GROUP BY category
        """)

        if cat_stats:
            df_cat = pd.DataFrame(cat_stats)
            st.markdown("##### Events by Category")
            st.dataframe(df_cat, use_container_width=True)
            st.bar_chart(df_cat.set_index("category")["event_count"])

    # ---------------- TAB 6: ADMIN PROFILE SETTINGS ----------------
    with tabs[5]:
        st.markdown("### Administrator Profile & Account Settings")
        st.caption("Update executive administrator contact info and upload your official platform avatar photo.")

        col_ap1, col_ap2 = st.columns([1, 2])
        with col_ap1:
            render_html(
                f'<div style="text-align: center; padding: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; margin-bottom: 12px;">'
                f'<div style="margin-bottom: 8px;">{get_user_avatar_html(user, size=84)}</div>'
                f'<div style="font-weight: 700; color: #0A2540; font-size: 1.05rem;">{user["full_name"]}</div>'
                f'<div style="font-size: 0.8rem; color: #64748B;">{user["email"]}</div>'
                f'<div style="margin-top: 6px;"><span class="simats-badge" style="background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; font-size: 0.72rem;">Super-Administrator</span></div>'
                f'</div>'
            )

        with col_ap2:
            with st.form("admin_profile_form"):
                adm_name = st.text_input("Administrator Full Name", value=user["full_name"])
                adm_phone = st.text_input("Contact Phone Number", value=user.get("phone") or "")
                adm_dept = st.text_input("Office / Unit", value=user.get("department") or "Academic Affairs & Oversight")

                adm_avatar_file = st.file_uploader(
                    "Upload / Replace Profile Photo (PNG/JPG)",
                    type=["png", "jpg", "jpeg"],
                    key="uploader_admin_avatar",
                    help="Upload a high-resolution professional headshot. Stored securely on the local server."
                )

                submit_adm_prof = st.form_submit_button("💾 Save Administrator Profile", type="primary")
                if submit_adm_prof:
                    new_avatar_rel = user.get("avatar_url")
                    if adm_avatar_file is not None:
                        os.makedirs(AVATARS_DIR, exist_ok=True)
                        avatar_filename = f"avatar_user_{user['id']}_{int(datetime.datetime.now().timestamp())}_{adm_avatar_file.name.replace(' ', '_')}"
                        avatar_abs_path = os.path.join(AVATARS_DIR, avatar_filename)
                        with open(avatar_abs_path, "wb") as af:
                            af.write(adm_avatar_file.getbuffer())
                        new_avatar_rel = f"static/avatars/{avatar_filename}"

                    ok, msg = update_user_profile(
                        user_id=user["id"],
                        full_name=adm_name,
                        phone=adm_phone,
                        institution=user.get("institution") or "SIMATS",
                        department=adm_dept,
                        avatar_url=new_avatar_rel
                    )
                    if ok:
                        st.success("✅ " + msg)
                        refreshed = execute_query_one("SELECT * FROM users WHERE id = ?", (user["id"],))
                        st.session_state["user"] = dict(refreshed)
                        st.rerun()
                    else:
                        st.error("❌ " + msg)
