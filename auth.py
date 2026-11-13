"""
SIMATS Event Sphere - Authentication & Access Control Module
Handles user registration, login, role-based access control,
domain verification for internal SIMATS students, and session state.
"""

import re
import streamlit as st
from database import (
    execute_query_one,
    execute_insert,
    execute_write,
    hash_password,
    verify_password,
    log_audit,
    create_notification
)

# Configurable internal domain allowlist
INTERNAL_DOMAINS = ["@simats.edu", "@saveetha.com"]


def is_internal_email(email: str) -> bool:
    """Check if an email matches the internal SIMATS domain allowlist."""
    email_clean = email.strip().lower()
    return any(email_clean.endswith(domain) for domain in INTERNAL_DOMAINS)


def register_user(
    email: str,
    password: str,
    full_name: str,
    phone: str = "",
    institution: str = "",
    department: str = ""
) -> tuple[bool, str]:
    """
    Register a student/participant account.
    - If email matches internal domain -> automatically internal_verified (fee permanently ₹0.00).
    - If email is non-matching -> external participant.
    - Security rule: Organizers and Admins cannot self-register.
    """
    email_clean = email.strip().lower()
    if not email_clean or not password or not full_name:
        return False, "Email, password, and full name are required."

    # Validate email format
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email_clean):
        return False, "Please enter a valid email address."

    # Check if user already exists
    existing = execute_query_one("SELECT id FROM users WHERE email = ?", (email_clean,))
    if existing:
        return False, "An account with this email already exists. Please log in."

    # Determine classification
    if is_internal_email(email_clean):
        category = "internal_verified"
        if not institution:
            institution = "SIMATS Deemed University"
    else:
        category = "external"
        if not institution:
            return False, "External participants must provide their institution or organization name."

    # Password hash
    pwd_hash = hash_password(password)

    try:
        user_id = execute_insert("""
        INSERT INTO users (email, password_hash, role, category, full_name, phone, institution, department)
        VALUES (?, ?, 'student', ?, ?, ?, ?, ?)
        """, (email_clean, pwd_hash, category, full_name.strip(), phone.strip(), institution.strip(), department.strip()))

        log_audit(user_id, "USER_REGISTERED", "users", user_id, f"Self-registered as {category} student.")
        create_notification(user_id, f"Welcome to SIMATS Event Sphere, {full_name}! Account created as {category.replace('_', ' ').title()}.")
        return True, "Registration successful! You may now log in."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"


def authenticate_user(email: str, password: str) -> tuple[bool, dict | str]:
    """Validate credentials and return user dict if successful."""
    email_clean = email.strip().lower()
    user = execute_query_one("""
    SELECT id, email, password_hash, role, category, full_name, phone, institution, department, avatar_url, created_at
    FROM users WHERE email = ?
    """, (email_clean,))

    if not user:
        return False, "No account found with that email address."

    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password. Please try again."

    # Clean out password hash before returning user object
    user_dict = dict(user)
    user_dict.pop("password_hash", None)
    log_audit(user_dict["id"], "USER_LOGIN", "users", user_dict["id"], "User logged in successfully.")
    return True, user_dict


def create_organizer_by_admin(
    admin_id: int,
    email: str,
    password: str,
    full_name: str,
    phone: str,
    institution: str,
    department: str
) -> tuple[bool, str]:
    """
    Exclusively allows Administrators to provision Event Organizer accounts.
    """
    email_clean = email.strip().lower()
    existing = execute_query_one("SELECT id FROM users WHERE email = ?", (email_clean,))
    if existing:
        return False, "An account with this email already exists."

    category = "internal_verified" if is_internal_email(email_clean) else "external"
    pwd_hash = hash_password(password)

    try:
        org_id = execute_insert("""
        INSERT INTO users (email, password_hash, role, category, full_name, phone, institution, department)
        VALUES (?, ?, 'organizer', ?, ?, ?, ?, ?)
        """, (email_clean, pwd_hash, category, full_name.strip(), phone.strip(), institution.strip(), department.strip()))

        log_audit(admin_id, "ORGANIZER_CREATED", "users", org_id, f"Organizer account created for {email_clean} by Admin ID {admin_id}")
        create_notification(org_id, "Your SIMATS Event Organizer account has been authorized. You can now publish and manage events.")
        return True, "Organizer account created successfully."
    except Exception as e:
        return False, f"Failed to create organizer: {str(e)}"


def update_user_profile(user_id: int, full_name: str, phone: str, institution: str, department: str, avatar_url: str = None) -> tuple[bool, str]:
    """
    Update basic profile details.
    Guarantees:
    - Internal status CANNOT be revoked or modified to bypass fee rules.
    - Role cannot be elevated via profile edit.
    """
    try:
        current = execute_query_one("SELECT category, role FROM users WHERE id = ?", (user_id,))
        if not current:
            return False, "User not found."

        # If internal, institution remains SIMATS
        inst = "SIMATS Deemed University" if current["category"] == "internal_verified" and not institution else institution

        if avatar_url is not None:
            execute_write("""
            UPDATE users
            SET full_name = ?, phone = ?, institution = ?, department = ?, avatar_url = ?
            WHERE id = ?
            """, (full_name.strip(), phone.strip(), inst.strip(), department.strip(), avatar_url.strip(), user_id))
        else:
            execute_write("""
            UPDATE users
            SET full_name = ?, phone = ?, institution = ?, department = ?
            WHERE id = ?
            """, (full_name.strip(), phone.strip(), inst.strip(), department.strip(), user_id))

        log_audit(user_id, "PROFILE_UPDATED", "users", user_id, "User updated personal profile details.")
        return True, "Profile updated successfully."
    except Exception as e:
        return False, f"Update failed: {str(e)}"


# Streamlit Session State Management Helpers
def init_session_state():
    """Ensure session state variables are initialized."""
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Landing"
    if "active_event_id" not in st.session_state:
        st.session_state["active_event_id"] = None
    if "pending_payment" not in st.session_state:
        st.session_state["pending_payment"] = None


def get_current_user() -> dict | None:
    """Retrieve currently authenticated user from session state."""
    return st.session_state.get("user")


def set_current_user(user_dict: dict | None):
    """Set the current user in session state."""
    st.session_state["user"] = user_dict


def logout_user():
    """Log out the current user and reset session state."""
    if st.session_state.get("user"):
        log_audit(st.session_state["user"]["id"], "USER_LOGOUT", "users", st.session_state["user"]["id"], "User logged out.")
    st.session_state["user"] = None
    st.session_state["current_page"] = "Landing"
    st.session_state["active_event_id"] = None
    st.session_state["pending_payment"] = None


def is_authenticated() -> bool:
    """Check if a user is currently logged in."""
    return st.session_state.get("user") is not None


def has_role(allowed_roles: list[str]) -> bool:
    """Check if currently logged-in user possesses one of the allowed roles."""
    user = get_current_user()
    if not user:
        return False
    return user.get("role") in allowed_roles
