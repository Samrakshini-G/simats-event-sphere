"""
SIMATS Event Sphere - Styling & University Branding Theme
Academic Navy (#0A2540, #1B365D), Warm Gold (#C5A059).
Crisp card containers, zero dead whitespace, tight spacing,
responsive image scaling, high-contrast status badges.
"""

import streamlit as st


def apply_theme():
    """Injects custom CSS for a clean, deployment-ready university portal."""
    st.markdown("""
    <style>
    /* ---- Google Fonts ---- */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:wght@600;700;800&display=swap');

    /* ---- Hide Streamlit chrome that creates a white strip at the top ---- */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { visibility: hidden; }
    .stDeployButton { display: none !important; }

    /* ---- Base typography ---- */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ---- Brand color tokens ---- */
    :root {
        --simats-navy:        #0A2540;
        --simats-navy-mid:    #1B365D;
        --simats-navy-deep:   #0D1E35;
        --simats-gold:        #C5A059;
        --simats-gold-hover:  #B38E46;
        --simats-gold-light:  #FBF7EE;
        --simats-bg:          #F5F7FA;
        --simats-card-border: #E2E8F0;
        --simats-text:        #0F172A;
        --simats-muted:       #64748B;
        --simats-green:       #10B981;
        --simats-danger:      #EF4444;
    }

    /* ---- App background: remove all default top padding ---- */
    .stApp {
        background-color: var(--simats-bg);
        color: var(--simats-text);
    }

    /* Eliminate Streamlit's default block padding that leaves a whitespace strip */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        max-width: 1340px !important;
    }

    /* Tighten Streamlit's internal vertical stack gap */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0 !important;
    }

    section[data-testid="stMain"] > div {
        padding-top: 0 !important;
    }

    /* ---- Top navigation bar ---- */
    .simats-topnav {
        background: #FFFFFF;
        border-bottom: 2px solid var(--simats-gold);
        padding: 0.6rem 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0;
        position: sticky;
        top: 0;
        z-index: 999;
        box-shadow: 0 2px 10px rgba(10,37,64,0.08);
    }

    .simats-topnav-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .simats-topnav-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-weight: 700;
        color: var(--simats-navy);
        font-size: 1.3rem;
        line-height: 1.1;
    }

    .simats-topnav-sub {
        font-size: 0.7rem;
        color: var(--simats-muted);
        font-weight: 500;
        letter-spacing: 0.3px;
        margin-top: 1px;
    }

    /* ---- Hero Banner ---- */
    .simats-hero-wrapper {
        position: relative;
        width: 100%;
        overflow: hidden;
        margin-bottom: 0;
        line-height: 0;
    }

    .simats-hero-img {
        width: 100%;
        height: 400px;
        object-fit: cover;
        display: block;
        filter: brightness(0.72) saturate(1.1);
    }

    .simats-hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            160deg,
            rgba(10,37,64,0.55) 0%,
            rgba(10,37,64,0.78) 55%,
            rgba(10,37,64,0.92) 100%
        );
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 2.5rem 3rem;
        color: #FFFFFF;
    }

    .hero-pill {
        display: inline-block;
        background: rgba(197,160,89,0.22);
        color: #FCD34D;
        border: 1px solid rgba(197,160,89,0.5);
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .hero-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 2.6rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.12;
        margin: 0 0 4px 0;
    }

    .hero-tagline {
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--simats-gold);
        letter-spacing: 0.5px;
        margin: 0 0 10px 0;
    }

    .hero-desc {
        color: #CBD5E1;
        font-size: 0.9rem;
        margin: 0 0 18px 0;
        max-width: 680px;
        line-height: 1.5;
    }

    .hero-pill-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }

    .hero-feature-pill {
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #FFFFFF;
    }

    .hero-cta-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 4px;
    }

    .hero-cta-btn {
        display: inline-block;
        padding: 10px 26px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.92rem;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.18s ease;
        letter-spacing: 0.2px;
    }

    .hero-cta-primary {
        background: var(--simats-gold);
        color: var(--simats-navy);
        border: 2px solid var(--simats-gold);
    }

    .hero-cta-primary:hover {
        background: var(--simats-gold-hover);
        border-color: var(--simats-gold-hover);
    }

    .hero-cta-outline {
        background: transparent;
        color: #FFFFFF;
        border: 2px solid rgba(255,255,255,0.6);
    }

    .hero-cta-outline:hover {
        background: rgba(255,255,255,0.1);
        border-color: #FFFFFF;
    }

    /* ---- Section header ---- */
    .simats-section-hdr {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin: 1.4rem 0 0.65rem 0;
        flex-wrap: wrap;
        gap: 4px;
    }

    .simats-section-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--simats-navy);
        margin: 0;
    }

    .simats-section-sub {
        font-size: 0.8rem;
        color: var(--simats-muted);
    }

    .simats-divider {
        border: none;
        border-top: 1px solid #E2E8F0;
        margin: 1.1rem 0 0.8rem 0;
    }

    /* ---- Cards (generic) ---- */
    .simats-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        transition: box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .simats-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 14px rgba(10,37,64,0.06);
    }

    /* ---- Event cards ---- */
    .simats-event-card-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 5px rgba(0,0,0,0.04);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .simats-event-card-container:hover {
        border-color: var(--simats-gold);
        box-shadow: 0 6px 20px rgba(10,37,64,0.08);
    }

    .simats-poster-img {
        width: 100%;
        height: 185px;
        object-fit: cover;
        border-radius: 7px;
        display: block;
    }

    /* ---- Feature highlight card ---- */
    .simats-feature-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .simats-feature-img {
        width: 100%;
        height: 155px;
        object-fit: cover;
        display: block;
    }
    .simats-feature-body {
        padding: 0.75rem 0.9rem 0.9rem 0.9rem;
        flex: 1;
    }

    /* ---- Achievement card ---- */
    .simats-achievement-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: box-shadow 0.15s ease;
    }
    .simats-achievement-card:hover {
        box-shadow: 0 4px 12px rgba(10,37,64,0.08);
    }
    .simats-achievement-img {
        width: 100%;
        height: 125px;
        object-fit: cover;
        display: block;
    }

    /* ---- Metric boxes ---- */
    .simats-metric-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.8rem 1.1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        border-left: 4px solid var(--simats-navy-mid);
    }
    .simats-metric-box.gold  { border-left-color: var(--simats-gold); }
    .simats-metric-box.green { border-left-color: var(--simats-green); }

    .simats-metric-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--simats-muted);
        margin-bottom: 0.1rem;
    }
    .simats-metric-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: var(--simats-navy);
        line-height: 1.2;
    }

    /* ---- Badges ---- */
    .simats-badge {
        display: inline-block;
        padding: 0.18rem 0.52rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .badge-internal {
        background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0;
    }
    .badge-external {
        background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE;
    }
    .badge-gold {
        background: #FFFBEB; color: #92400E; border: 1px solid #FCD34D;
    }
    .badge-status-open {
        background: #ECFDF5; color: #065F46; border: 1px solid #6EE7B7;
    }
    .badge-status-pending {
        background: #FFFBEB; color: #92400E; border: 1px solid #FCD34D;
    }
    .badge-status-draft {
        background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;
    }
    .badge-status-completed {
        background: #F0FDF4; color: #166534; border: 1px solid #86EFAC;
    }
    .badge-status-rejected, .badge-status-cancelled {
        background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA;
    }

    /* ---- CTA buttons (Streamlit native) ---- */
    .stButton > button {
        border-radius: 7px;
        font-weight: 700;
        font-size: 0.88rem;
        padding: 0.42rem 0.9rem;
        transition: all 0.15s ease;
        letter-spacing: 0.1px;
    }

    /* Primary buttons: gold-on-navy */
    .stButton > button[kind="primary"] {
        background: var(--simats-gold) !important;
        color: var(--simats-navy) !important;
        border: 2px solid var(--simats-gold) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--simats-gold-hover) !important;
        border-color: var(--simats-gold-hover) !important;
    }

    /* ---- Form inputs ---- */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea {
        border-radius: 7px;
        font-size: 0.9rem;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 6px 14px;
        font-weight: 600;
        font-size: 0.85rem;
        border-radius: 6px 6px 0 0;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background: var(--simats-navy) !important;
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: var(--simats-navy-mid);
        color: #FFFFFF;
        border: 1px solid rgba(197,160,89,0.3);
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--simats-gold);
        color: var(--simats-navy);
        border-color: var(--simats-gold);
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--simats-gold) !important;
        color: var(--simats-navy) !important;
        border-color: var(--simats-gold) !important;
    }

    /* ---- Ticket container ---- */
    .ticket-container {
        background: #FFFFFF;
        border: 2px dashed var(--simats-gold);
        border-radius: 12px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-top: 0.4rem;
    }

    /* ---- Auth page wrapper ---- */
    .simats-auth-wrapper {
        max-width: 540px;
        margin: 1.5rem auto 0 auto;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 2rem 2.2rem 1.75rem 2.2rem;
        box-shadow: 0 4px 20px rgba(10,37,64,0.07);
    }

    /* ---- Certificate section card ---- */
    .simats-cert-card {
        background: #FFFFFF;
        border: 1px solid var(--simats-gold);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 14px rgba(10,37,64,0.05);
        margin-top: 0.8rem;
    }

    /* ---- Footer ---- */
    .simats-footer {
        text-align: center;
        padding: 1.2rem 0 0.5rem 0;
        color: #94A3B8;
        font-size: 0.78rem;
        border-top: 1px solid #E2E8F0;
        margin-top: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
