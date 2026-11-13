"""
SIMATS Event Sphere - Public Landing Page & Event Discovery Module
Features centered official university branding, clean unobstructed round campus
hero banner, structured campus highlights, prominent student authentication options,
and robust HTML-safe event card rendering.
"""

import os
import textwrap
import streamlit as st
from event_service import get_public_events, EVENT_CATEGORIES, EVENT_FORMATS
from auth import is_authenticated, get_current_user
from asset_helper import (
    ASSETS,
    CAMPUS_HIGHLIGHTS,
    ACHIEVEMENT_ITEMS,
    get_event_poster_path,
    get_image_base64
)


def render_landing_view():
    """
    Render the clean, unobstructed public landing page with strict hierarchy:
    1. Centered & highlighted 'SIMATS Event Sphere' top header
    2. Unobstructed clean round campus building image (assets/landing/hero_campus.jpg)
    3. 'SIMATS Engineering' + 'Engineered to Excellence' tagline & institutional overview
    4. Campus Highlights & Academic Facilities section
    5. Clean, prominent Sign In and Register options + footer contact/email details
    """
    user = get_current_user()

    # Pre-encode local images as high-performance base64 data URIs
    logo_college_b64 = get_image_base64(ASSETS["logo_college"])
    logo_eng_b64 = get_image_base64(ASSETS["logo_engineering"])
    hero_b64 = get_image_base64(ASSETS.get("hero_campus", ASSETS["hero_banner"]))

    # =========================================================================
    # 1. TOP HEADER: CENTERED & HIGHLIGHTED PROJECT TITLE
    # =========================================================================
    header_html = textwrap.dedent(f"""
    <div style="text-align: center; padding: 0.5rem 0 0.8rem 0; border-bottom: 2px solid #C5A059; margin-bottom: 0.85rem; background: #FFFFFF; border-radius: 10px; box-shadow: 0 2px 8px rgba(10,37,64,0.04);">
        <div style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-bottom: 4px;">
            <img src="{logo_college_b64}" style="height: 48px; width: auto; object-fit: contain;" alt="SIMATS Crest"/>
            <img src="{logo_eng_b64}" style="height: 40px; width: auto; object-fit: contain;" alt="SIMATS Engineering"/>
        </div>
        <h1 style="font-family: 'Playfair Display', Georgia, serif; font-weight: 800; color: #0A2540; font-size: 2.35rem; margin: 2px 0 2px 0; letter-spacing: -0.5px; line-height: 1.15;">
            SIMATS Event Sphere
        </h1>
        <div style="font-size: 0.85rem; color: #64748B; font-weight: 600; letter-spacing: 0.5px;">
            Saveetha Institute of Medical and Technical Sciences &bull; Deemed to be University
        </div>
    </div>
    """).strip()
    st.markdown(header_html, unsafe_allow_html=True)

    # Quick action row at top (if logged in, shows user pill & dashboard button)
    if user:
        col_u1, col_u2 = st.columns([7, 3])
        with col_u1:
            st.caption(f"Signed in as **{user['full_name']}** ({user['role'].title()})")
        with col_u2:
            if user["role"] == "student":
                if st.button("🎓 Go to Participant Dashboard", key="btn_top_dash", type="primary", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.rerun()

    # =========================================================================
    # 2. CLEAN HERO BANNER IMAGE (NO TEXT OVERLAYS - UNOBSTRUCTED)
    # =========================================================================
    hero_html = textwrap.dedent(f"""
    <div style="width: 100%; border-radius: 14px; overflow: hidden; margin: 0.4rem 0 1.4rem 0; box-shadow: 0 6px 24px rgba(10,37,64,0.1); border: 1px solid #E2E8F0;">
        <img src="{hero_b64}" style="width: 100%; height: 420px; object-fit: cover; display: block;" alt="SIMATS Campus Round Building"/>
    </div>
    """).strip()
    st.markdown(hero_html, unsafe_allow_html=True)

    # =========================================================================
    # 3. CONTENT HIERARCHY BELOW THE IMAGE:
    #    (1) SIMATS ENGINEERING, TAGLINE & INSTITUTIONAL DESCRIPTION
    # =========================================================================
    branding_html = textwrap.dedent("""
    <div style="text-align: center; max-width: 880px; margin: 0 auto 1.4rem auto; padding: 0 0.5rem;">
        <span class="hero-pill" style="margin-bottom: 8px;">🏛️ Official University Central Event Portal &bull; Est. 1988</span>
        <h2 style="font-family: 'Playfair Display', Georgia, serif; font-size: 2.1rem; font-weight: 800; color: #0A2540; margin: 4px 0 4px 0; line-height: 1.15;">
            SIMATS Engineering
        </h2>
        <div style="font-size: 1.2rem; font-weight: 700; color: #C5A059; letter-spacing: 0.5px; margin-bottom: 10px;">
            Engineered to Excellence
        </div>
        <p style="color: #475569; font-size: 0.96rem; line-height: 1.6; margin: 0 0 14px 0;">
            Central institutional event management and discovery platform for national hackathons,
            international research symposiums, cutting-edge medical workshops, cultural fests,
            and multidisciplinary student innovation at Saveetha Institute of Medical and Technical Sciences.
        </p>
        <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <span class="simats-badge badge-internal" style="font-size: 0.78rem; padding: 5px 14px;">✨ ₹0.00 Fee for SIMATS Students</span>
            <span class="simats-badge" style="background: rgba(197, 160, 89, 0.18); color: #92400E; border: 1px solid rgba(197, 160, 89, 0.5); font-size: 0.78rem; padding: 5px 14px;">🎫 Live QR Attendance Passes</span>
            <span class="simats-badge" style="background: rgba(59, 130, 246, 0.12); color: #1E40AF; border: 1px solid rgba(59, 130, 246, 0.35); font-size: 0.78rem; padding: 5px 14px;">📜 Tamper-Evident PDF Certificates</span>
            <span class="simats-badge" style="background: rgba(15, 23, 42, 0.08); color: #0F172A; border: 1px solid rgba(15, 23, 42, 0.2); font-size: 0.78rem; padding: 5px 14px;">🔒 Role-Protected Portals</span>
        </div>
    </div>
    """).strip()
    st.markdown(branding_html, unsafe_allow_html=True)

    # =========================================================================
    # 3. CONTENT HIERARCHY BELOW THE IMAGE:
    #    (2) CAMPUS HIGHLIGHTS & ACADEMIC FACILITIES
    # =========================================================================
    st.markdown("<h4 style='color: #0A2540; margin: 1.2rem 0 0.6rem 0;'>🏛️ Campus Highlights & Academic Facilities</h4>", unsafe_allow_html=True)

    col_h1, col_h2, col_h3 = st.columns(3)
    cols = [col_h1, col_h2, col_h3]
    for idx, item in enumerate(CAMPUS_HIGHLIGHTS):
        with cols[idx]:
            img_b64 = get_image_base64(item["path"])
            facility_html = textwrap.dedent(f"""
            <div class="simats-feature-card">
                <img class="simats-feature-img" src="{img_b64}" alt="{item['title']}"/>
                <div class="simats-feature-body">
                    <div>
                        <span style="font-size: 0.7rem; font-weight: 700; color: #C5A059; text-transform: uppercase; letter-spacing: 0.5px;">
                            {item['subtitle']}
                        </span>
                        <div style="font-size: 0.95rem; font-weight: 700; color: #0A2540; margin: 2px 0 4px 0;">
                            {item['title']}
                        </div>
                        <p style="font-size: 0.8rem; color: #64748B; margin: 0; line-height: 1.35;">
                            {item['description']}
                        </p>
                    </div>
                </div>
            </div>
            """).strip()
            st.markdown(facility_html, unsafe_allow_html=True)

    # =========================================================================
    # 3. CONTENT HIERARCHY BELOW THE IMAGE:
    #    (3) UNIVERSITY ACCREDITATIONS, RESEARCH METRICS & KEY MILESTONES
    # =========================================================================
    st.markdown("<h4 style='color: #0A2540; margin: 1.4rem 0 0.6rem 0;'>🏆 University Accreditations & Key Milestones</h4>", unsafe_allow_html=True)

    ach_cols = st.columns(5)
    for idx, ach in enumerate(ACHIEVEMENT_ITEMS):
        with ach_cols[idx]:
            ach_b64 = get_image_base64(ach["path"])
            ach_html = textwrap.dedent(f"""
            <div class="simats-achievement-card">
                <img class="simats-achievement-img" src="{ach_b64}" alt="{ach['title']}"/>
                <div style="padding: 8px 10px;">
                    <div style="font-size: 0.82rem; font-weight: 700; color: #0A2540; line-height: 1.25; margin-bottom: 2px;">
                        {ach['title']}
                    </div>
                    <div style="font-size: 0.72rem; color: #64748B; line-height: 1.2;">
                        {ach['caption']}
                    </div>
                </div>
            </div>
            """).strip()
            st.markdown(ach_html, unsafe_allow_html=True)

    # =========================================================================
    # 4. PROMINENT SIGN IN & REGISTER OPTIONS + FOOTER CONTACT/EMAIL
    # =========================================================================
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Prominent Participant Access Container
    with st.container():
        st.markdown(textwrap.dedent("""
        <div style="background: #FFFFFF; border: 2px solid #C5A059; border-radius: 12px; padding: 1.4rem; box-shadow: 0 4px 16px rgba(10,37,64,0.06); margin-bottom: 1.2rem;">
            <div style="text-align: center; margin-bottom: 0.8rem;">
                <h3 style="color: #0A2540; font-family: 'Playfair Display', Georgia, serif; margin: 0 0 4px 0;">
                    🎓 Participant Access & Event Discovery
                </h3>
                <p style="color: #64748B; font-size: 0.9rem; margin: 0;">
                    Sign in to access registered events, visual QR attendance tickets, and verified certificates.
                    Institutional SIMATS emails (@simats.edu) qualify for automatic ₹0.00 registration fee waivers.
                </p>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)

        if not user:
            col_cta1, col_cta2, col_cta3 = st.columns([1, 1, 1])
            with col_cta1:
                if st.button("🔑 Student Sign In", key="btn_cta_signin", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Authentication"
                    st.rerun()
            with col_cta2:
                if st.button("📝 Register New Participant", key="btn_cta_register", type="primary", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Authentication"
                    st.rerun()
            with col_cta3:
                if st.button("🔍 Explore Campus Events", key="btn_cta_explore_events", use_container_width=True):
                    st.session_state["current_page"] = "Events"
                    st.rerun()
        else:
            col_lg1, col_lg2 = st.columns(2)
            with col_lg1:
                if st.button("🎓 Open Participant Dashboard", key="btn_cta_dash_open", type="primary", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.rerun()
            with col_lg2:
                if st.button("🔍 Browse & Register for Events", key="btn_cta_browse_events", use_container_width=True):
                    st.query_params["view"] = "student"
                    st.session_state["current_page"] = "Student Dashboard"
                    st.session_state["student_active_tab"] = "Event Registration & Discovery"
                    st.rerun()

    # Footer with Official University Contact and Email Details
    footer_html = textwrap.dedent(f"""
    <div class="simats-footer" style="margin-top: 1.5rem; padding: 1.2rem 0; border-top: 1px solid #E2E8F0; text-align: center; color: #64748B; font-size: 0.82rem;">
        <div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 6px;">
            <img src="{logo_college_b64}" style="height: 28px; width: auto;" alt="SIMATS"/>
            <span style="font-weight: 700; color: #0A2540; font-size: 0.9rem;">Saveetha Institute of Medical and Technical Sciences</span>
        </div>
        <p style="margin: 0 0 4px 0;">Saveetha Nagar, Thandalam, Chennai - 602 105, Tamil Nadu, India &bull; Deemed to be University under Section 3 of the UGC Act, 1956</p>
        <p style="margin: 0 0 4px 0; color: #475569;">
            <strong>Official Contacts:</strong> Email: <a href="mailto:events@simats.edu" style="color: #0A2540; font-weight: 600;">events@simats.edu</a> &bull; Phone: +91 44 2680 1999 &bull; Website: <a href="https://simats.edu" target="_blank" style="color: #C5A059; font-weight: 600;">www.simats.edu</a>
        </p>
        <p style="margin: 2px 0 0 0; color: #94A3B8; font-size: 0.75rem;">SIMATS Event Sphere &bull; Engineered to Excellence &bull; NAAC A++ Accredited &bull; NIRF Top Ranked</p>
    </div>
    """).strip()
    st.markdown(footer_html, unsafe_allow_html=True)


def render_event_discovery_view():
    """
    Render the dedicated public Event Discovery view with clean, HTML-safe event cards
    and dynamic custom poster image rendering without leaking raw HTML tags.
    """
    user = get_current_user()

    # Navigation header
    col_back, col_title = st.columns([2, 8])
    with col_back:
        if st.button("← Back to Campus Home", key="btn_events_back_home"):
            st.session_state["current_page"] = "Landing"
            st.rerun()
    with col_title:
        st.markdown("""
        <h3 style="color: #0A2540; margin: 0; font-family: 'Playfair Display', Georgia, serif;">
            Explore Approved University Events
        </h3>
        <span style="font-size: 0.82rem; color: #64748B;">
            Live registration, automated ₹0 waivers, and official participation passes
        </span>
        """, unsafe_allow_html=True)

    # Search & Filter Toolbar
    col_search, col_cat, col_fmt, col_fee = st.columns([3, 2, 2, 2])
    with col_search:
        search_query = st.text_input("Search Events", placeholder="Search by title, topic, or venue...", label_visibility="collapsed", key="ed_search")
    with col_cat:
        category_filter = st.selectbox("Category", ["All"] + EVENT_CATEGORIES, label_visibility="collapsed", key="ed_cat")
    with col_fmt:
        format_filter = st.selectbox("Format", ["All"] + EVENT_FORMATS, label_visibility="collapsed", key="ed_fmt")
    with col_fee:
        fee_filter = st.selectbox("Fee Type", ["All", "Free (₹0)", "Paid (External)"], label_visibility="collapsed", key="ed_fee")

    date_tab = st.radio("Timeline Filter", ["Upcoming", "All", "Past Events"], horizontal=True, label_visibility="collapsed", key="ed_timeline")

    events = get_public_events(
        search=search_query,
        category=category_filter,
        format_type=format_filter,
        fee_filter=fee_filter,
        date_filter=date_tab
    )

    if not events:
        st.info("No approved events found matching your filter criteria.")
        return

    st.caption(f"Showing **{len(events)}** approved event{'s' if len(events) != 1 else ''}:")

    for ev in events:
        poster_path = get_event_poster_path(ev)
        poster_b64 = get_image_base64(poster_path)

        with st.container():
            # Robust, unindented HTML card without HTML comments to ensure zero leaked raw code
            card_html = textwrap.dedent(f"""
            <div class="simats-event-card-container">
            <div style="display: flex; flex-direction: row; gap: 16px; padding: 14px; flex-wrap: wrap;">
            <div style="flex: 0 0 200px; max-width: 200px; min-width: 160px;">
            <img src="{poster_b64}" class="simats-poster-img" alt="{ev['title']} poster"/>
            </div>
            <div style="flex: 1; min-width: 260px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
            <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 6px; flex-wrap: wrap;">
            <span class="simats-badge badge-internal">{ev['category']}</span>
            <span class="simats-badge badge-external">{ev['format']}</span>
            <span class="simats-badge badge-status-open">{ev['effective_status']}</span>
            </div>
            <h3 style="margin: 0 0 4px 0; color: #0A2540; font-size: 1.25rem; font-weight: 700;">
            {ev['title']}
            </h3>
            <p style="color: #475569; font-size: 0.88rem; margin: 0 0 8px 0; line-height: 1.35;">
            {ev['summary'] or (ev['description'][:130] + '...')}
            </p>
            <div style="display: flex; gap: 16px; font-size: 0.8rem; color: #64748B; flex-wrap: wrap;">
            <div><strong>📅 Date:</strong> {ev['start_time'][:16]}</div>
            <div><strong>📍 Venue:</strong> {ev['venue']}</div>
            <div><strong>👥 Registrations:</strong> {ev['registered_count']}/{ev['capacity']}</div>
            </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #E2E8F0; flex-wrap: wrap;">
            <div style="display: flex; gap: 12px; align-items: center;">
            <span style="font-size: 0.8rem; color: #065F46; font-weight: 700; background: #ECFDF5; padding: 2px 8px; border-radius: 4px; border: 1px solid #A7F3D0;">
            🎓 SIMATS Students: ₹0.00 (Free)
            </span>
            <span style="font-size: 0.8rem; color: #1E40AF; font-weight: 600;">
            External: {'₹' + str(int(ev['external_fee'])) if ev['external_fee'] > 0 else 'Free'}
            </span>
            </div>
            </div>
            </div>
            </div>
            </div>
            """).strip()
            st.markdown(card_html, unsafe_allow_html=True)

            col_exp, col_act = st.columns([7, 3])
            with col_exp:
                with st.expander(f"📋 View Full Agenda & Details for '{ev['title']}'"):
                    st.markdown(f"**Full Description:**\n{ev['description']}")
                    if ev.get("agenda"):
                        st.markdown(f"**Event Schedule / Agenda:**\n{ev['agenda']}")
                    st.markdown(f"**Faculty Organizer:** {ev['organizer_name']} ({ev.get('organizer_email', '')})")
                    if ev.get("signatory_name"):
                        st.markdown(f"**Certificate Signatory:** {ev['signatory_name']}, {ev.get('signatory_title', '')}")
                    st.caption(f"Registration Window: {ev['reg_start']} to {ev['reg_end']}")

            with col_act:
                if not is_authenticated():
                    if st.button("🎓 Sign In to Register", key=f"btn_disc_login_{ev['id']}", use_container_width=True):
                        st.query_params["view"] = "student"
                        st.session_state["current_page"] = "Authentication"
                        st.session_state["active_event_id"] = ev["id"]
                        st.rerun()
                else:
                    if user["role"] == "student":
                        if ev["effective_status"] in ["Registration Open", "Published"]:
                            if st.button("Register for Event", key=f"btn_disc_reg_{ev['id']}", type="primary", use_container_width=True):
                                st.query_params["view"] = "student"
                                st.session_state["current_page"] = "Student Dashboard"
                                st.session_state["student_active_tab"] = "Event Registration & Discovery"
                                st.session_state["active_event_id"] = ev["id"]
                                st.rerun()
                        else:
                            st.button(f"{ev['effective_status']}", key=f"btn_disc_dis_{ev['id']}", disabled=True, use_container_width=True)
                    else:
                        st.caption(f"Signed in as {user['role'].title()}.")
