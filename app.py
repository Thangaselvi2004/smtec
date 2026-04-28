import streamlit as st
import pandas as pd
import os
from src.utils import load_config, render_sidebar, render_header
from src.auth import init_session, login_user, register_user, logout_user
from src.database import get_user_points

# Page Config
st.set_page_config(
    page_title="Student AI | Home",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Typography
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
<style>
    * { font-family: 'Outfit', sans-serif; }
    
    /* Advanced Palette & Background */
    .stApp {
        background: radial-gradient(circle at top left, #fdf2f8 0%, #ffffff 40%),
                    radial-gradient(circle at bottom right, #f5f3ff 0%, #ffffff 40%),
                    #ffffff;
    }
    
    /* Glassmorphism Login */
    .login-container {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px) saturate(180%);
        padding: 50px;
        border-radius: 30px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.05),
                    0 0 0 1px rgba(255, 255, 255, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.3);
        margin: 40px auto;
        max-width: 480px;
    }
    
    /* Hero Title with Fluid Gradient */
    .hero-title {
        font-size: 3.8rem;
        font-weight: 800;
        letter-spacing: -2px;
        line-height: 1.1;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #ec4899 10%, #3b82f6 50%, #8b5cf6 90%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradient-shift 8s ease infinite;
    }
    
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Premium Feature Cards */
    .card-shell {
        background: white;
        padding: 30px;
        border-radius: 24px;
        border: 1px solid #f1f5f9;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.02), 0 4px 6px -4px rgba(0, 0, 0, 0.02);
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: center;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .card-shell::after {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(to right, #ec4899, #3b82f6, #8b5cf6);
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .card-shell:hover {
        transform: translateY(-12px);
        box-shadow: 0 25px 50px -12px rgba(139, 92, 246, 0.15);
        border-color: #e2e8f0;
    }
    
    .card-shell:hover::after {
        opacity: 1;
    }
    
    .card-icon {
        font-size: 3rem;
        margin-bottom: 20px;
        display: inline-block;
        transition: transform 0.3s;
    }
    
    .card-shell:hover .card-icon {
        transform: scale(1.2) rotate(5deg);
    }
    
    /* Vibrant Interaction Elements */
    .stButton > button {
        border-radius: 16px !important;
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 14px 30px !important;
        box-shadow: 0 10px 20px -5px rgba(236, 72, 153, 0.4) !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 20px 30px -5px rgba(139, 92, 246, 0.5) !important;
        transform: translateY(-2px);
    }
    
    /* Sidebar Overrides */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session
init_session()

# Authentication Check
if not st.session_state.get('authenticated', False):
    # --- PREMIUM LOGIN PAGE ---
    _, col, _ = st.columns([1, 4, 1])
    with col:
        st.write("###")
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 40px;">
            <div style="font-size: 5rem; margin-bottom: 10px; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.1));">✨</div>
            <h1 style="color: #1e293b; font-size: 4rem; font-weight: 800; letter-spacing: -3px; margin:0;">Student AI</h1>
            <p style="color: #64748b; font-size: 1.25rem; font-weight: 400;">Your Premium Academic Intelligence Portal</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            tab_login, tab_signup = st.tabs(["🔐 Sign In", "🚀 Register"])
            
            with tab_login:
                with st.form("login_form"):
                    u = st.text_input("Username", placeholder="e.g. jdoe_01")
                    p = st.text_input("Password", type="password", placeholder="••••••••")
                    st.write("")
                    if st.form_submit_button("Enter Workspace"):
                        if login_user(u, p):
                            st.success("Welcome back!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
            
            with tab_signup:
                with st.form("signup_form"):
                    nu = st.text_input("Choose Username")
                    np = st.text_input("Secure Password", type="password")
                    cp = st.text_input("Confirm Password", type="password")
                    st.write("")
                    if st.form_submit_button("Create My Account"):
                        if np != cp: st.error("Passwords do not match")
                        elif len(np) < 4: st.error("Minimum 4 characters")
                        else:
                            if register_user(nu, np, role='Student'):
                                st.success("Account Ready! Please Sign In.")
                            else: st.error("Username already exists")
            st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- AUTHENTICATED APP CONTENT ---

# Sidebar & Header
render_sidebar()
render_header("🏠 Home")

# Hero Section
st.markdown(f"""
<div style="background: white; padding: 80px 40px; border-radius: 32px; text-align: center; margin-bottom: 50px; box-shadow: 0 20px 50px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;">
    <h1 class="hero-title">Elevate Your Performance, {st.session_state.get('username', 'Scholar')}.</h1>
    <p style="color: #475569; font-size: 1.5rem; max-width: 800px; margin: 0 auto 40px auto; line-height: 1.6;">
        Harness the power of AI-driven analytics to master your courses and land your dream career.
    </p>
    <div style="display: flex; justify-content: center; gap: 50px;">
        <div>
            <h2 style="margin:0; font-size: 3rem; background: linear-gradient(135deg, #ec4899, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{get_user_points(st.session_state['user_id'])}</h2>
            <p style="color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem;">Career Points</p>
        </div>
        <div style="width: 1px; background: #e2e8f0; height: 60px;"></div>
        <div>
            <h2 style="margin:0; font-size: 3rem; color: #10b981;">Active</h2>
            <p style="color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem;">Account Tier</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Grid
st.markdown("<h3 style='color: #1e293b; font-weight: 700; margin-bottom: 25px;'>🚀 Productivity Suite</h3>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

features = [
    ("📊", "Dashboard", "Real-time insights into your academic journey.", "pages/1_Dashboard.py", "nav_dash"),
    ("🔮", "AI Predictor", "Forecast grades with machine learning models.", "pages/2_Prediction.py", "nav_pred"),
    ("📚", "Syllabus", "Strategize your learning goals and curriculum.", "pages/9_Syllabus.py", "nav_syll"),
    ("🎯", "Placement Hub", "Master the interviews with AI-ready prep.", "pages/12_Placement_Hub.py", "nav_place")
]

for i, (icon, title, desc, path, key) in enumerate(features):
    with [c1, c2, c3, c4][i]:
        st.markdown(f"""
        <div class="card-shell">
            <span class="card-icon">{icon}</span>
            <h4 style="color: #1e293b; margin-bottom: 10px; font-weight: 700;">{title}</h4>
            <p style="color: #64748b; font-size: 0.95rem; line-height: 1.5; margin-bottom: 25px;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Open {title}", key=key, use_container_width=True):
            st.switch_page(path)

st.divider()

# Secondary Insights
cola, colb = st.columns(2)
with cola:
    st.markdown("""
    <div style="background: white; padding: 40px; border-radius: 28px; border: 1px solid #f1f5f9; box-shadow: 0 10px 25px rgba(0,0,0,0.02); height: 100%;">
        <h4 style="margin-top:0; color: #1e293b; font-weight: 700;">🛠️ Analysis Framework</h4>
        <p style="color: #64748b; margin-bottom: 20px;">Deep-dive into model mechanics and data structures.</p>
        <ul style="color: #475569; line-height: 2; padding-left: 20px;">
            <li><b>Model Insights</b>: Interpret AI decision making.</li>
            <li><b>Data Hub</b>: Export and manage your datasets.</li>
            <li><b>Library</b>: Digital resource management system.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with colb:
    st.markdown("""
    <div style="background: white; padding: 40px; border-radius: 28px; border: 1px solid #f5f3ff; box-shadow: 0 10px 25px rgba(139, 92, 246, 0.03); height: 100%;">
        <h4 style="margin-top:0; color: #7c3aed; font-weight: 700;">🤖 Intelligence Cloud</h4>
        <p style="color: #6d28d9; margin-bottom: 20px;">Powered by our custom academic LLMs.</p>
        <ul style="color: #6d28d9; line-height: 2; padding-left: 20px;">
            <li><b>Conversational AI</b>: Real-time academic tutor.</li>
            <li><b>Interview Simulator</b>: Roleplay technical rounds.</li>
            <li><b>GPA Forecaster</b>: Dynamic grade point projection.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.write("###")
st.markdown("""
<div style="background: linear-gradient(90deg, #fdf2f8, #f5f3ff); padding: 20px 30px; border-radius: 16px; border-left: 5px solid #ec4899;">
    <span style="color: #be185d; font-weight: 700;">✨ Pro Tip:</span> 
    <span style="color: #475569;">Use 'Mock Challenge' in the Placement Hub to warm up for technical assessments!</span>
</div>
""", unsafe_allow_html=True)
