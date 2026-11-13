"""
SIMATS Event Sphere - Public Certificate Verification View Module
Publicly accessible portal allowing employers, academic institutions,
and third parties to verify certificate authenticity without disclosing private participant data.
Uses official local assets for university seal and certificate presentation.
"""

import streamlit as st
from certificate_service import verify_certificate_public
from database import execute_query
from asset_helper import ASSETS, get_image_base64


def render_verify_view():
    """Render the public certificate verification interface."""
    logo_b64 = get_image_base64(ASSETS["logo_college"])
    cert_tmpl_b64 = get_image_base64(ASSETS["certificate_template"])

    st.markdown(f"""
    <div class="simats-brand-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <img src="{logo_b64}" style="height: 52px; width: auto;" alt="SIMATS"/>
                <div>
                    <span style="background: rgba(197, 160, 89, 0.25); color: #C5A059; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;">
                        Official University Registry
                    </span>
                    <h1 style="margin: 4px 0 2px 0; font-size: 1.8rem;">SIMATS Certificate Verification</h1>
                    <p style="font-size: 0.9rem; margin: 0;">Public Credential Validation System &bull; Saveetha Institute of Medical and Technical Sciences</p>
                </div>
            </div>
            <div style="text-align: right; margin-top: 6px;">
                <span style="font-size: 0.8rem; color: #CBD5E1;">Deemed University &bull; Chennai, India</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='color: #0A2540; margin: 0 0 4px 0;'>Verify Official Academic Credential</h4>", unsafe_allow_html=True)
    st.caption("Verify the legitimacy of SIMATS participation and achievement credentials issued by university event organizers.")

    # Check for sample certificates to test with
    sample_certs = execute_query("SELECT certificate_id FROM certificates WHERE status = 'Issued' LIMIT 3")
    sample_ids = [c["certificate_id"] for c in sample_certs] if sample_certs else ["SIMATS-CERT-2026-001"]

    if sample_ids:
        st.write("💡 **Quick Test Identifiers:**")
        cols = st.columns(len(sample_ids))
        for i, sid in enumerate(sample_ids):
            with cols[i]:
                if st.button(f"Test: {sid}", key=f"btn_test_cert_{sid}", use_container_width=True):
                    st.session_state["verify_cert_input"] = sid

    col_q, col_act = st.columns([5, 2])
    with col_q:
        cert_query = st.text_input(
            "Certificate ID",
            value=st.session_state.get("verify_cert_input", ""),
            placeholder="e.g. SIMATS-CERT-2026-001",
            label_visibility="collapsed"
        )
    with col_act:
        run_search = st.button("🔍 Verify Authenticity", type="primary", use_container_width=True)

    if run_search or cert_query:
        if not cert_query.strip():
            st.warning("Please provide a Certificate ID to verify.")
        else:
            ok, msg, data = verify_certificate_public(cert_query.strip())
            
            if ok:
                st.success("✅ **Official University Credential Verified!**")
                
                # Render verified university seal container with local template thumbnail
                st.markdown(f"""
                <div style="background: #FFFFFF; border: 2px solid #C5A059; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 18px rgba(10,37,64,0.06); margin-top: 0.75rem;">
                    <div style="display: flex; gap: 20px; align-items: center; border-bottom: 2px solid #1B365D; padding-bottom: 0.75rem; margin-bottom: 1rem;">
                        <img src="{logo_b64}" style="height: 50px; width: auto;" alt="SIMATS Seal"/>
                        <div>
                            <h3 style="color: #1B365D; margin: 0; font-family: 'Playfair Display', Georgia, serif; font-size: 1.25rem;">
                                SAVEETHA INSTITUTE OF MEDICAL AND TECHNICAL SCIENCES
                            </h3>
                            <p style="color: #C5A059; margin: 2px 0 0 0; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px;">
                                OFFICIAL VERIFICATION OF ACADEMIC PARTICIPATION
                            </p>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem;">
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Recipient Name</span>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #0A2540;">{data['recipient_name']}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Affiliation / Institution</span>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #334155;">{data['institution']}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Event Title</span>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #1B365D;">"{data['event_title']}"</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Category</span>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #334155;">{data['event_category']}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Event Date</span>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #334155;">{data['event_date'][:16]}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Date of Issuance</span>
                            <div style="font-size: 0.95rem; font-weight: 600; color: #334155;">{data['issue_date'][:10]}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Certificate ID</span>
                            <div style="font-size: 0.95rem; font-family: monospace; font-weight: 700; color: #1B365D;">{data['certificate_id']}</div>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Registry Status</span>
                            <div><span class="simats-badge badge-status-completed" style="font-size: 0.8rem;">{data['status']}</span></div>
                        </div>
                    </div>

                    <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px dashed #CBD5E1; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div>
                            <span style="font-size: 0.75rem; color: #64748B;">Authorized Signatory:</span><br/>
                            <strong style="color: #0A2540; font-size: 0.9rem;">{data['signatory']}</strong>
                        </div>
                        <div style="text-align: right; margin-top: 4px;">
                            <span style="font-size: 0.75rem; color: #059669; font-weight: 600;">
                                🔒 Cryptographically Logged &amp; Attendance-Verified
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.error(f"❌ {msg}")
                st.info("Please verify that the Certificate ID was entered correctly without typos.")
