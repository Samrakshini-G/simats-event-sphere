"""
SIMATS Event Sphere - Authentication View Module
Handles Student/Participant Login and Registration, with separate dedicated
portals for Faculty Coordinators and Central Administrators.
Enforces strict role protection and domain-based fee waivers.
"""

import streamlit as st
from auth import (
    authenticate_user,
    register_user,
    set_current_user,
    is_internal_email,
    INTERNAL_DOMAINS
)
from asset_helper import get_image_base64, ASSETS


def render_student_auth_view():
    """
    Render public authentication exclusively for Students & Participants.
    Admin and Coordinator options are strictly omitted from this public view.
    """
    logo_b64 = get_image_base64(ASSETS["logo_college"])

    if st.button("← Return to Campus Events & Discovery", key="btn_auth_back_landing_stud"):
        st.session_state["current_page"] = "Landing"
        st.rerun()

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <img src="{logo_b64}" style="height: 60px; margin-bottom: 8px;" alt="SIMATS Logo"/>
        <h2 style="color: #0A2540; font-family: 'Playfair Display', Georgia, serif; margin: 0 0 4px 0;">
            Student & Participant Portal
        </h2>
        <p style="color: #64748B; font-size: 0.95rem; margin: 0;">
            Access your registered events, visual QR tickets, and verified university certificates
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1-Click Fast Switcher strictly for Student Evaluation
    with st.expander("⚡ 1-Click Student Demo Switcher (For Evaluation & Testing)", expanded=True):
        st.caption("Quickly test student participant workflows without typing:")
        col_c, col_d = st.columns(2)

        with col_c:
            if st.button("🎓 SIMATS Student (₹0 Waiver)", help="arun.v@simats.edu (Instant ₹0)", key="btn_demo_stud", use_container_width=True):
                ok, user = authenticate_user("arun.v@simats.edu", "Student@123")
                if ok:
                    set_current_user(user)
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.rerun()

        with col_d:
            if st.button("🌐 External Participant", help="karthik.external@gmail.com", key="btn_demo_ext", use_container_width=True):
                ok, user = authenticate_user("karthik.external@gmail.com", "External@123")
                if ok:
                    set_current_user(user)
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.rerun()

    auth_tab_login, auth_tab_reg = st.tabs(["🔑 Student Sign In", "📝 Register New Participant"])

    # ---------------- STUDENT LOGIN TAB ----------------
    with auth_tab_login:
        st.markdown("#### Enter Student / Participant Credentials")
        with st.form("student_login_form"):
            login_email = st.text_input("Registered Email Address", placeholder="e.g. arun.v@simats.edu or user@gmail.com")
            login_password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Sign In to Student Portal", type="primary", use_container_width=True)

            if submit_login:
                if not login_email or not login_password:
                    st.error("Please provide both email address and password.")
                else:
                    success, res = authenticate_user(login_email, login_password)
                    if success:
                        set_current_user(res)
                        st.success(f"Welcome back, {res['full_name']}!")
                        st.query_params["view"] = "student"
                        st.session_state["current_page"] = "Student Dashboard"
                        if st.session_state.get("active_event_id"):
                            st.session_state["student_active_tab"] = "Event Registration & Discovery"
                        st.rerun()
                    else:
                        st.error(res)

    # ---------------- STUDENT REGISTRATION TAB ----------------
    with auth_tab_reg:
        st.markdown("#### Create a Participant Account")
        st.caption("All SIMATS institutional email domains (@simats.edu, @saveetha.com) qualify for permanent ₹0.00 event fee waivers.")

        reg_email = st.text_input("Email Address", key="reg_email_field", placeholder="student@simats.edu (Internal) or name@example.com (External)")

        # Dynamic domain verification feedback
        if reg_email:
            if is_internal_email(reg_email):
                st.success("✅ **SIMATS Internal Domain Detected (@simats.edu)!** You qualify for `internal_verified` status. All event registration fees are permanently waived to **₹0.00**.")
            else:
                st.info("🌐 **External Participant Email:** You will register as an external participant. Event fees set by organizers will apply for paid events.")

        with st.form("student_registration_form"):
            reg_name = st.text_input("Full Name *", placeholder="Dr./Mr./Ms. Full Name")
            reg_pwd = st.text_input("Password *", type="password")
            reg_phone = st.text_input("Mobile Phone Number", placeholder="+91 98765 43210")
            
            # Institution field defaults if internal
            default_inst = "SIMATS Deemed University" if is_internal_email(reg_email) else ""
            reg_inst = st.text_input("Institution / Organization *", value=default_inst, placeholder="e.g. Saveetha School of Engineering or Anna University")
            reg_dept = st.text_input("Department / Specialization", placeholder="e.g. Computer Science, Biotechnology, Mechanical")

            submit_reg = st.form_submit_button("Create Participant Account", type="primary", use_container_width=True)

            if submit_reg:
                ok, msg = register_user(
                    email=reg_email,
                    password=reg_pwd,
                    full_name=reg_name,
                    phone=reg_phone,
                    institution=reg_inst,
                    department=reg_dept
                )
                if ok:
                    st.success(msg)
                    # Automatically authenticate new user and redirect smoothly into Student Portal
                    auth_ok, user_data = authenticate_user(reg_email, reg_pwd)
                    if auth_ok:
                        set_current_user(user_data)
                        st.query_params["view"] = "student"
                        st.session_state["current_page"] = "Student Dashboard"
                        if st.session_state.get("active_event_id"):
                            st.session_state["student_active_tab"] = "Event Registration & Discovery"
                        st.rerun()
                    else:
                        st.info("Account created successfully! Please sign in above.")
                else:
                    st.error(msg)


def render_coordinator_auth_view():
    """
    Render dedicated authentication strictly for Event Coordinators & Organizers.
    Direct URL access only (/?view=coordinator).
    """
    logo_b64 = get_image_base64(ASSETS["logo_college"])

    if st.button("← Return to Campus Events & Discovery", key="btn_auth_back_landing_coord"):
        st.query_params["view"] = "student"
        st.session_state["current_page"] = "Landing"
        st.rerun()

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <img src="{logo_b64}" style="height: 60px; margin-bottom: 8px;" alt="SIMATS Logo"/>
        <h2 style="color: #0A2540; font-family: 'Playfair Display', Georgia, serif; margin: 0 0 4px 0;">
            🏛️ Event Coordinator Portal
        </h2>
        <p style="color: #64748B; font-size: 0.95rem; margin: 0;">
            Restricted Entry: Department Coordinators, Faculty Organizers & Attendance Controllers
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚡ 1-Click Coordinator Demo Switcher", expanded=True):
        if st.button("🏛️ Faculty Coordinator Sign In", help="organizer@simats.edu", key="btn_demo_coord", use_container_width=True):
            ok, user = authenticate_user("organizer@simats.edu", "Organizer@123")
            if ok:
                set_current_user(user)
                st.query_params["view"] = "coordinator"
                st.session_state["current_page"] = "Organizer Dashboard"
                st.rerun()

    st.markdown("#### Enter Coordinator Credentials")
    with st.form("coordinator_login_form"):
        login_email = st.text_input("Coordinator Email Address", placeholder="organizer@simats.edu")
        login_password = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Sign In to Coordinator Portal", type="primary", use_container_width=True)

        if submit_login:
            if not login_email or not login_password:
                st.error("Please provide both email and password.")
            else:
                success, res = authenticate_user(login_email, login_password)
                if success:
                    # Enforce server-side role check
                    if res["role"] not in ["organizer", "admin"]:
                        st.error("⛔ Access Denied: Your account is registered as a Student. Only authorized Faculty Coordinators can access this portal.")
                    else:
                        set_current_user(res)
                        st.success(f"Welcome, Coordinator {res['full_name']}!")
                        st.query_params["view"] = "coordinator"
                        st.session_state["current_page"] = "Organizer Dashboard"
                        st.rerun()
                else:
                    st.error(res)

    st.caption("ℹ️ Coordinator accounts are provisioned exclusively by University Administrators. Contact admin@simats.edu for authorization.")


def render_admin_auth_view():
    """
    Render dedicated authentication strictly for Central Administrators.
    Direct URL access only (/?view=admin).
    """
    logo_b64 = get_image_base64(ASSETS["logo_college"])

    if st.button("← Return to Campus Events & Discovery", key="btn_auth_back_landing_admin"):
        st.query_params["view"] = "student"
        st.session_state["current_page"] = "Landing"
        st.rerun()

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <img src="{logo_b64}" style="height: 60px; margin-bottom: 8px;" alt="SIMATS Logo"/>
        <h2 style="color: #0A2540; font-family: 'Playfair Display', Georgia, serif; margin: 0 0 4px 0;">
            👑 SIMATS Central Administration Console
        </h2>
        <p style="color: #64748B; font-size: 0.95rem; margin: 0;">
            High-Security Access: Academic Controllers, Deans & Platform Super-Administrators Only
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚡ 1-Click Super-Admin Demo Switcher", expanded=True):
        if st.button("👑 System Administrator Sign In", help="admin@simats.edu", key="btn_demo_admin", use_container_width=True):
            ok, user = authenticate_user("admin@simats.edu", "Admin@123")
            if ok:
                set_current_user(user)
                st.query_params["view"] = "admin"
                st.session_state["current_page"] = "Admin Dashboard"
                st.rerun()

    st.markdown("#### Enter Administrator Credentials")
    with st.form("admin_login_form"):
        login_email = st.text_input("Administrator Email Address", placeholder="admin@simats.edu")
        login_password = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Sign In to Admin Console", type="primary", use_container_width=True)

        if submit_login:
            if not login_email or not login_password:
                st.error("Please provide both email and password.")
            else:
                success, res = authenticate_user(login_email, login_password)
                if success:
                    # Enforce server-side role check
                    if res["role"] != "admin":
                        st.error("⛔ Access Denied: Administrator clearance is required. Your account does not possess Super-Admin privileges.")
                    else:
                        set_current_user(res)
                        st.success(f"Welcome, Administrator {res['full_name']}!")
                        st.query_params["view"] = "admin"
                        st.session_state["current_page"] = "Admin Dashboard"
                        st.rerun()
                else:
                    st.error(res)


def render_auth_view():
    """Default entrypoint for backward compatibility: renders student auth."""
    render_student_auth_view()
