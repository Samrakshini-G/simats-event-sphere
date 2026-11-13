"""
SIMATS Event Sphere - Main Streamlit Application Orchestrator
Coordinates navigation, role-based access control, session lifecycle,
university branding, strict asset usage, and separate entry URLs.

Portals:
  - Public Landing & Student Portal: /?view=student (or /)
  - Coordinator Portal: /?view=coordinator (direct URL access only, role-protected)
  - Admin Portal: /?view=admin (direct URL access only, role-protected)
"""

import importlib
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="SIMATS Event Sphere",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Core imports
from database import init_db, seed_database, execute_query_one
from auth import (
    init_session_state,
    get_current_user,
    set_current_user,
    logout_user,
    is_authenticated,
    authenticate_user
)
import styles
import asset_helper
from styles import apply_theme
from asset_helper import ASSETS, get_image_base64, get_user_avatar_html, render_html, clean_html

# Views
import views.landing
import views.auth_view
import views.student_dashboard
import views.organizer_dashboard
import views.admin_dashboard
import views.verify_view

# Force live reload of view modules to prevent stale cached versions in running servers
importlib.reload(styles)
importlib.reload(asset_helper)
importlib.reload(views.landing)
importlib.reload(views.auth_view)
importlib.reload(views.student_dashboard)
importlib.reload(views.organizer_dashboard)
importlib.reload(views.admin_dashboard)
importlib.reload(views.verify_view)

from views.landing import render_landing_view, render_event_discovery_view
from views.auth_view import (
    render_student_auth_view,
    render_coordinator_auth_view,
    render_admin_auth_view
)
from views.student_dashboard import render_student_dashboard
from views.organizer_dashboard import render_organizer_dashboard
from views.admin_dashboard import render_admin_dashboard
from views.verify_view import render_verify_view

# Ensure DB schema & seed data are initialized
init_db()
seed_database()

# Apply custom CSS styling
apply_theme()

# Initialize session state variables
init_session_state()


def main():
    """Main routing, role protection, and sidebar execution."""
    user = get_current_user()

    # Determine requested entry URL view via query parameters
    view_param = st.query_params.get("view", "").lower().strip()

    # Query unread notifications count if user logged in
    unread_count = 0
    if user:
        notif_row = execute_query_one(
            "SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],)
        )
        unread_count = notif_row["c"] if notif_row else 0

    logo_b64 = get_image_base64(ASSETS["logo_college"])

    # =========================================================================
    # ROUTE 1: COORDINATOR PORTAL (/?view=coordinator) - Direct Access Only
    # =========================================================================
    if view_param == "coordinator":
        with st.sidebar:
            render_html(
                f'<div style="text-align: center; padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(197, 160, 89, 0.3); margin-bottom: 0.75rem;">'
                f'<img src="{logo_b64}" style="height: 55px; width: auto; margin-bottom: 6px;" alt="SIMATS"/>'
                f'<h3 style="color: #FFFFFF; margin: 0; font-family: Playfair Display, Georgia, serif; font-size: 1.3rem;">Coordinator Portal</h3>'
                f'<span style="color: #C5A059; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Department &amp; Faculty Office</span>'
                f'</div>'
            )

            if user:
                role_label = user["role"].title()
                av_html = get_user_avatar_html(user, size=38)
                render_html(
                    f'<div style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(197, 160, 89, 0.3); border-radius: 8px; padding: 10px 12px; margin-bottom: 0.75rem;">'
                    f'<div style="display: flex; align-items: center; gap: 10px;">'
                    f'{av_html}'
                    f'<div>'
                    f'<div style="font-size: 0.72rem; color: #CBD5E1;">Coordinator:</div>'
                    f'<div style="font-weight: 700; color: #FFFFFF; font-size: 0.92rem; line-height: 1.2;">{user["full_name"]}</div>'
                    f'<div style="margin-top: 3px;"><span class="simats-badge badge-internal" style="font-size: 0.65rem;">{role_label}</span></div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )

                if unread_count > 0:
                    st.info(f"🔔 You have **{unread_count}** unread notification{'s' if unread_count != 1 else ''}!")

            # Navigation for authorized coordinators
            if user and user["role"] in ["organizer", "admin"]:
                coord_nav_options = ["🏛️ Coordinator Workspace", "🎓 Participant View", "🔍 Verify Certificate (Public)"]
                if user["role"] == "admin":
                    coord_nav_options.insert(0, "👑 Admin Console")

                selected_coord_nav = st.radio(
                    "Coordinator Nav",
                    coord_nav_options,
                    index=0 if st.session_state.get("coord_nav") not in coord_nav_options else coord_nav_options.index(st.session_state["coord_nav"]),
                    label_visibility="collapsed"
                )
                st.session_state["coord_nav"] = selected_coord_nav

                st.divider()
                if st.button("🚪 Sign Out", key="sb_coord_signout", use_container_width=True):
                    logout_user()
                    st.rerun()

            st.write("")
            if st.button("🌐 Switch to Public Landing", key="btn_coord_to_public", use_container_width=True):
                st.query_params["view"] = "student"
                st.session_state["current_page"] = "Landing"
                st.rerun()

        # Server-Side Role Authorization for Coordinator Route
        if not user:
            render_coordinator_auth_view()
            return
        elif user["role"] not in ["organizer", "admin"]:
            st.error("⛔ **Access Denied: Coordinator Clearance Required**")
            st.warning(f"Your active account (**{user['full_name']}**, {user['role'].title()}) does not possess faculty coordinator authorization.")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Return to Student Portal", type="primary", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.rerun()
            with col_b2:
                if st.button("Sign Out to Switch Accounts", use_container_width=True):
                    logout_user()
                    st.rerun()
            return
        else:
            current_choice = st.session_state.get("coord_nav", "🏛️ Coordinator Workspace")
            if current_choice == "👑 Admin Console" and user["role"] == "admin":
                render_admin_dashboard()
            elif current_choice == "🎓 Participant View":
                render_student_dashboard()
            elif current_choice == "🔍 Verify Certificate (Public)":
                render_verify_view()
            else:
                render_organizer_dashboard()
            return

    # =========================================================================
    # ROUTE 2: ADMIN PORTAL (/?view=admin) - Direct Access Only
    # =========================================================================
    elif view_param == "admin":
        with st.sidebar:
            render_html(
                f'<div style="text-align: center; padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(197, 160, 89, 0.3); margin-bottom: 0.75rem;">'
                f'<img src="{logo_b64}" style="height: 55px; width: auto; margin-bottom: 6px;" alt="SIMATS"/>'
                f'<h3 style="color: #FFFFFF; margin: 0; font-family: Playfair Display, Georgia, serif; font-size: 1.3rem;">Admin Console</h3>'
                f'<span style="color: #C5A059; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Super-Administrator Oversight</span>'
                f'</div>'
            )

            if user:
                av_html = get_user_avatar_html(user, size=38)
                render_html(
                    f'<div style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(197, 160, 89, 0.3); border-radius: 8px; padding: 10px 12px; margin-bottom: 0.75rem;">'
                    f'<div style="display: flex; align-items: center; gap: 10px;">'
                    f'{av_html}'
                    f'<div>'
                    f'<div style="font-size: 0.72rem; color: #CBD5E1;">Administrator:</div>'
                    f'<div style="font-weight: 700; color: #FFFFFF; font-size: 0.92rem; line-height: 1.2;">{user["full_name"]}</div>'
                    f'<div style="margin-top: 3px;"><span class="simats-badge badge-internal" style="background: #FEF3C7; color: #92400E; font-size: 0.65rem;">👑 Super-Admin</span></div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )

            # Navigation for authenticated Admins
            if user and user["role"] == "admin":
                admin_nav_options = ["👑 Admin Console", "🏛️ Coordinator Portal", "🎓 Participant View", "🔍 Verify Certificate (Public)"]
                selected_adm_nav = st.radio(
                    "Admin Nav",
                    admin_nav_options,
                    index=0 if st.session_state.get("admin_nav") not in admin_nav_options else admin_nav_options.index(st.session_state["admin_nav"]),
                    label_visibility="collapsed"
                )
                st.session_state["admin_nav"] = selected_adm_nav

                st.divider()
                if st.button("🚪 Sign Out", key="sb_admin_signout", use_container_width=True):
                    logout_user()
                    st.rerun()

            st.write("")
            if st.button("🌐 Switch to Public Landing", key="btn_admin_to_public", use_container_width=True):
                st.query_params["view"] = "student"
                st.session_state["current_page"] = "Landing"
                st.rerun()

        # Server-Side Role Authorization for Admin Route
        if not user:
            render_admin_auth_view()
            return
        elif user["role"] != "admin":
            st.error("⛔ **Access Denied: Administrator Clearance Required**")
            st.warning(f"Your active account (**{user['full_name']}**, {user['role'].title()}) does not possess Super-Administrator privileges.")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                dest_view = "coordinator" if user["role"] == "organizer" else "student"
                dest_page = "Organizer Dashboard" if user["role"] == "organizer" else "Student Dashboard"
                if st.button(f"Return to {user['role'].title()} Portal", type="primary", use_container_width=True):
                    st.query_params["view"] = dest_view
                    st.session_state["current_page"] = dest_page
                    st.rerun()
            with col_b2:
                if st.button("Sign Out to Switch Accounts", use_container_width=True):
                    logout_user()
                    st.rerun()
            return
        else:
            current_choice = st.session_state.get("admin_nav", "👑 Admin Console")
            if current_choice == "🏛️ Coordinator Portal":
                render_organizer_dashboard()
            elif current_choice == "🎓 Participant View":
                render_student_dashboard()
            elif current_choice == "🔍 Verify Certificate (Public)":
                render_verify_view()
            else:
                render_admin_dashboard()
            return

    # =========================================================================
    # ROUTE 3: STUDENT PORTAL & PUBLIC LANDING (/?view=student or /)
    # Strict Student-Facing Public Interface: No Admin or Coordinator Buttons!
    # =========================================================================
    else:
        with st.sidebar:
            render_html(
                f'<div style="text-align: center; padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(197, 160, 89, 0.3); margin-bottom: 0.75rem;">'
                f'<img src="{logo_b64}" style="height: 55px; width: auto; margin-bottom: 6px;" alt="SIMATS"/>'
                f'<h3 style="color: #FFFFFF; margin: 0; font-family: Playfair Display, Georgia, serif; font-size: 1.3rem;">SIMATS</h3>'
                f'<span style="color: #C5A059; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Event Sphere</span>'
                f'</div>'
            )

            # User Status Badge
            if user:
                role_label = user["role"].title()
                cat_label = "₹0 Internal Student" if user.get("category") == "internal_verified" else "External"
                av_html = get_user_avatar_html(user, size=38)
                render_html(
                    f'<div style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(197, 160, 89, 0.3); border-radius: 8px; padding: 10px 12px; margin-bottom: 0.75rem;">'
                    f'<div style="display: flex; align-items: center; gap: 10px;">'
                    f'{av_html}'
                    f'<div>'
                    f'<div style="font-size: 0.72rem; color: #CBD5E1;">Signed in as:</div>'
                    f'<div style="font-weight: 700; color: #FFFFFF; font-size: 0.92rem; line-height: 1.2;">{user["full_name"]}</div>'
                    f'<div style="display: flex; gap: 4px; margin-top: 3px; flex-wrap: wrap;">'
                    f'<span class="simats-badge badge-internal" style="font-size: 0.65rem;">{role_label}</span>'
                    f'<span class="simats-badge badge-external" style="font-size: 0.65rem;">{cat_label}</span>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )

                if unread_count > 0:
                    st.info(f"🔔 You have **{unread_count}** unread notification{'s' if unread_count != 1 else ''}!")

            # Dynamic Navigation Menu Options strictly for public / student view
            nav_options = ["🏛️ Campus Overview", "🔍 Event Discovery", "🔍 Verify Certificate (Public)"]

            if not user:
                nav_options.insert(2, "🎓 Student Sign In / Register")
            else:
                if user["role"] == "student":
                    nav_options.insert(0, "🎓 Participant Dashboard")
                else:
                    nav_options.insert(0, "🎓 Participant View")

            page_mapping = {
                "Landing": "🏛️ Campus Overview",
                "Events": "🔍 Event Discovery",
                "Authentication": "🎓 Student Sign In / Register",
                "Student Dashboard": "🎓 Participant Dashboard" if (user and user["role"] == "student") else "🎓 Participant View",
                "Verify Certificate": "🔍 Verify Certificate (Public)"
            }
            reverse_mapping = {v: k for k, v in page_mapping.items()}

            current_nav_label = page_mapping.get(st.session_state.get("current_page", "Landing"), "🏛️ Campus Overview")
            if current_nav_label not in nav_options:
                current_nav_label = nav_options[0]

            selected_nav = st.radio(
                "Navigate",
                nav_options,
                index=nav_options.index(current_nav_label),
                label_visibility="collapsed"
            )
            st.session_state["current_page"] = reverse_mapping.get(selected_nav, "Landing")

            st.divider()

            # Fast evaluation switcher strictly for students (No Admin or Coordinator buttons!)
            if not user:
                st.caption("⚡ Student Demo Switcher:")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button("🎓 Arun (₹0)", key="sb_stud_zero", use_container_width=True):
                        ok, u = authenticate_user("arun.v@simats.edu", "Student@123")
                        if ok:
                            set_current_user(u)
                            st.query_params["view"] = "student"
                            st.session_state["current_page"] = "Student Dashboard"
                            st.rerun()
                with col_s2:
                    if st.button("🌐 External", key="sb_stud_ext", use_container_width=True):
                        ok, u = authenticate_user("karthik.external@gmail.com", "External@123")
                        if ok:
                            set_current_user(u)
                            st.query_params["view"] = "student"
                            st.session_state["current_page"] = "Student Dashboard"
                            st.rerun()
            else:
                # If logged-in user is an administrator or coordinator exploring student view, offer link back
                if user["role"] == "organizer":
                    if st.button("🏛️ Return to Coordinator Portal", key="sb_back_to_coord", use_container_width=True):
                        st.query_params["view"] = "coordinator"
                        st.session_state["current_page"] = "Organizer Dashboard"
                        st.rerun()
                elif user["role"] == "admin":
                    if st.button("👑 Return to Admin Console", key="sb_back_to_adm", use_container_width=True):
                        st.query_params["view"] = "admin"
                        st.session_state["current_page"] = "Admin Dashboard"
                        st.rerun()

                st.write("")
                if st.button("🚪 Sign Out", key="sb_signout", use_container_width=True):
                    logout_user()
                    st.rerun()

        # View Routing for Student Portal & Landing Page
        page = st.session_state.get("current_page", "Landing")

        if page == "Landing":
            render_landing_view()
        elif page == "Events":
            render_event_discovery_view()
        elif page == "Authentication":
            render_student_auth_view()
        elif page == "Student Dashboard":
            if not user:
                render_student_auth_view()
            else:
                render_student_dashboard()
        elif page == "Verify Certificate":
            render_verify_view()
        else:
            render_landing_view()


if __name__ == "__main__":
    main()
