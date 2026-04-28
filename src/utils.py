import logging
import yaml
import os

def load_config(config_path="config/config.yaml"):
    """Loads the YAML configuration file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_logger(name):
    """Returns a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
    return logger
def render_header(title):
    """Renders a common header with a title and a logout button on the right."""
    import streamlit as st
    from src.auth import logout_user
    
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title(title)
    with col2:
        st.write("###") # Vertically align with title
        if st.button("🚪 Logout", key=f"top_logout_{title.replace(' ', '_')}", use_container_width=True):
            logout_user()

def render_sidebar():
    """Renders a common sidebar across all pages."""
    import streamlit as st
    from src.auth import logout_user
    from src.database import get_user_points, get_notifications, mark_notifications_read

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('username', 'User')}")
        st.caption(f"Role: **{st.session_state.get('role', 'N/A')}**")
        
        # Notifications Center
        st.divider()
        st.subheader("🔔 Notifications")
        notifications = get_notifications(st.session_state['user_id'], unread_only=True)
        if notifications:
            for n_id, msg, is_read, dt in notifications:
                st.caption(f"📍 {msg}")
            if st.button("Mark all as read", key="sidebar_notif_read"):
                mark_notifications_read(st.session_state['user_id'])
                st.rerun()
        else:
            st.caption("No new notifications.")
        st.divider()

        # Display Points
        points = get_user_points(st.session_state['user_id'])
        st.metric("🏆 Your Points", points)
        
        st.write("")
        if st.button("🚪 Logout", use_container_width=True, key="logout_button_sidebar"):
            logout_user()
        st.divider()
