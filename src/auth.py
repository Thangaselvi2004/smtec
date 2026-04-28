import streamlit as st
from src.database import check_user, add_user

def init_session():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'role' not in st.session_state:
        st.session_state['role'] = None

def login_user(username, password):
    """Authenticate user. Returns user data if successful, else None."""
    return check_user(username, password)

def st_login_user(username, password):
    """Streamlit-specific login helper."""
    user = login_user(username, password)
    if user:
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = user[0]
        st.session_state['username'] = user[1]
        st.session_state['role'] = user[2]
        return True
    return False

def register_user(username, password, role='Student', email=None):
    """Register a new user."""
    return add_user(username, password, role, email=email)

def logout_user():
    """Clear session state and logout."""
    st.session_state['authenticated'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None
    st.rerun()
