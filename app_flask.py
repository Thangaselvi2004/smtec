from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import os
import secrets
import random
import pandas as pd
from src.database import (
    get_user_points, get_student_progress, get_download_history, get_resources,
    get_db_connection, get_topic_note, save_topic_note, get_discussions, 
    add_discussion, update_points, add_notification, get_exams, add_exam,
    delete_exam, update_exam, add_todo, get_todos, toggle_todo, delete_todo,
    get_leaderboard, add_resource, delete_resource, update_resource, track_download,
    add_assigned_task, get_assigned_tasks_for_staff, get_assigned_tasks_for_student,
    toggle_assigned_task_completion, delete_assigned_task, get_task_completions,
    add_internal_mark, get_internal_marks, delete_internal_mark, update_internal_mark, record_attendance, get_attendance_report, update_attendance_status, delete_attendance,
    add_feedback, get_feedback_list,
    add_global_exam, get_global_exams, delete_global_exam, get_pending_task_count,
    mark_assigned_task_complete, get_user_by_id, update_user_profile, delete_user, change_user_role, update_password_by_email,
    add_question_pdf, get_question_pdfs, delete_question_pdf,
    update_user_class_details,
    add_activity_log, get_all_activity_logs
)
from src.auth import login_user, register_user
from src.syllabus_data import SYLLABUS_DATA

app = Flask(__name__)
# Use a persistent secret key so sessions survive restarts
_secret_key_file = os.path.join(os.path.dirname(__file__), '.flask_secret')
if os.path.exists(_secret_key_file):
    with open(_secret_key_file, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(16)
    with open(_secret_key_file, 'w') as f:
        f.write(app.secret_key)


# Decorators
def staff_only(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['Staff', 'Admin']:
            flash('Access Denied. Staff/Admin only.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Admin':
            flash('Access Denied. Admins only.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Global context processors for templates
@app.context_processor
def inject_globals():
    user_id = session.get('user_id')
    pending_count = 0
    if user_id and session.get('role') == 'Student':
        pending_count = get_pending_task_count(user_id)
        
    return dict(
        user_id=user_id, 
        username=session.get('username'),
        pending_task_count=pending_count
    )

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('splash.html')
    
    points = get_user_points(session['user_id'])
    return render_template('index.html', points=points)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    points = get_user_points(user_id)
    total, completed, scores_df = get_student_progress(user_id)
    
    # Convert dataframe to list of dicts for template
    scores = scores_df.to_dict('records')
    progress_per = round((completed / total * 100), 1) if total > 0 else 0
    
    return render_template('dashboard.html', 
                           points=points, 
                           total=total, 
                           completed=completed, 
                           scores=scores, 
                           progress_per=progress_per)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user = login_user(email, password)
        if user:
            # user = (id, username, role, is_approved)
            user_role = user[2] or ''
            selected_role = (role or '').strip().title()

            # If the stored role is missing, persist the selected role
            if not user_role.strip() and selected_role:
                change_user_role(user[0], selected_role)
                user_role = selected_role

            if user_role.strip().lower() != selected_role.lower():
                flash('Selected role does not match your account.', 'error')
                return redirect(url_for('login'))
            if user[3] == 0:
                flash('Your account is pending admin approval. Please wait for access.', 'warning')
                return redirect(url_for('login'))
                
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user_role
            
            # Load year and department from database into session
            user_data = get_user_by_id(user[0])
            if user_data:
                session['user_year'] = user_data[6] or ''      # year
                session['user_department'] = user_data[7] or '' # department
            
            add_activity_log(user[0], 'LOGIN', f'{user[1]} logged in as {user_role}', request.remote_addr)
            flash('Welcome back!', 'success')
            
            # Redirect to next page for staff/student selection
            if user_role == 'Admin':
                return redirect(url_for('admin_portal'))
            else:
                return redirect(url_for('user_profile'))
        else:
            flash('Invalid credentials', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = (request.form.get('role', 'Student') or 'Student').strip().title()
        
        if len(password) < 4:
            flash('Password too short', 'error')
        else:
            # We use name as username and email as the identifier
            if register_user(name, password, role=role, email=email):
                add_activity_log(None, 'REGISTER', f'New {role} account: {name} ({email})', request.remote_addr)
                flash('Account created! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Email or identifier already in use', 'error')
                
    return render_template('register.html')

@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        role = request.form.get('role')
        year = request.form.get('year')
        department = request.form.get('department')
        class_section = request.form.get('class_section')
        
        # Store in session
        if role:
            session['role'] = role
        session['user_year'] = year
        session['user_department'] = department
        session['class_section'] = class_section
        
        # Persist year and department to database
        update_user_class_details(session['user_id'], year, department)
        
        # Redirect based on role
        role = session.get('role')
        if role == 'Admin':
            return redirect(url_for('admin_portal'))
        elif role == 'Staff':
            return redirect(url_for('staff_portal'))
        else:
            return redirect(url_for('index'))
    
    return render_template('user_profile.html')

@app.route('/logout')
def logout():
    uid = session.get('user_id')
    uname = session.get('username', 'Unknown')
    if uid:
        add_activity_log(uid, 'LOGOUT', f'{uname} logged out', request.remote_addr)
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        dob = request.form.get('dob', '').strip()

        if not email or not new_password or not confirm_password or not dob:
            flash('Please fill in all fields to reset your password.', 'error')
        elif new_password != confirm_password:
            flash('New password and confirmation do not match.', 'error')
        elif len(new_password) < 4:
            flash('Password must be at least 4 characters long.', 'error')
        else:
            if update_password_by_email(email, new_password):
                flash('Password reset successful. Please login with your new password.', 'success')
                return redirect(url_for('login'))
            else:
                flash('No account found with that email address.', 'error')

    return render_template('forgot_password.html')

# @app.route('/placement')
# def placement():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     
#     from src.placement_data import APTITUDE_QUESTIONS, TECH_INTERVIEW_QA
#     
# # Moved to global scope at line 23
# 
#     import random
#     
#     # Flatten categories for simple demo
#     all_apt = []
#     for cat in APTITUDE_QUESTIONS:
#         all_apt.extend(APTITUDE_QUESTIONS[cat])
#     
#     all_tech = []
#     for cat in TECH_INTERVIEW_QA:
#         all_tech.extend(TECH_INTERVIEW_QA[cat])
#     
#     apt_questions = random.sample(all_apt, min(5, len(all_apt)))
#     tech_qa = random.sample(all_tech, min(5, len(all_tech)))
#     
#     return render_template('placement.html', 
#                           apt_questions=apt_questions,
#                           tech_qa=tech_qa,
#                           interview_roles=list(INTERVIEW_DATA.keys()))

# @app.route('/api/interview/start', methods=['POST'])
# def api_interview_start():
#     role = request.json.get('role')
#     session['interview_role'] = role
#     session['interview_step'] = 0
#     return jsonify({'status': 'success', 'question': INTERVIEW_DATA[role][0], 'step': 1})
# 
# @app.route('/api/interview/next', methods=['POST'])
# def api_interview_next():
#     role = session.get('interview_role')
#     step = session.get('interview_step', 0)
#     
#     # Mock AI Feedback Analysis
#     ans = request.json.get('answer', '')
#     feedback = "Good response. Try to be more specific with examples."
#     if len(ans) > 50: feedback = "Excellent detail! You demonstrated strong understanding."
#     
#     step += 1
#     session['interview_step'] = step
#     
#     if step < len(INTERVIEW_DATA[role]):
#         return jsonify({
#             'status': 'continue', 
#             'question': INTERVIEW_DATA[role][step], 
#             'step': step + 1,
#             'feedback': feedback
#         })
#     else:
#         return jsonify({
#             'status': 'finished',
#             'feedback': "Great session! You showed confidence and good domain knowledge."
#         })

@app.route('/predictor', methods=['GET', 'POST'])
def predictor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Staff should use the Monitoring page instead
    if session.get('role') in ['Staff', 'Admin']:
        flash("Staff members use AI Analysis inside Student Monitoring.", "info")
        return redirect(url_for('student_monitoring'))

    import joblib
    from src.utils import load_config
    config = load_config()
    
    model_path = os.path.join(config['directories']['models'], config['files']['model'])
    scaler_path = os.path.join(config['directories']['models'], config['files']['scaler'])
    
    model = None
    scaler = None
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    
    points = get_user_points(session['user_id'])
    prediction = None
    recommendations = []
    
    if request.method == 'POST' and model:
        try:
            study_hours = float(request.form.get('study_hours', 5))
            attendance = float(request.form.get('attendance', 85))
            sleep_hours = float(request.form.get('sleep_hours', 7))
            participation = float(request.form.get('participation', 60))
            previous_grade = float(request.form.get('previous_grade', 75))
            points_input = float(request.form.get('points', points))
            
            # Feature Engineering
            engagement_score = (attendance * 0.6) + (participation * 0.4)
            studious_ratio = study_hours / (sleep_hours + 0.1)
            
            features = pd.DataFrame([[
                study_hours, attendance, sleep_hours, previous_grade, participation, points_input, engagement_score, studious_ratio
            ]], columns=['StudyHours', 'Attendance', 'SleepHours', 'PreviousGrade', 'Participation', 'Points', 'EngagementScore', 'StudiousRatio'])
            
            scaled_features = scaler.transform(features)
            prediction = round(model.predict(scaled_features)[0], 1)
            
            # Recommendations
            if attendance < 80: recommendations.append("📉 Attendance is low. Try to attend more classes.")
            if study_hours < 7: recommendations.append("⏳ Study hours are below average. Focus more on your subjects.")
            if points_input < 50: recommendations.append("🎮 LMS Activity is low. Earn more points by completing tasks.")
            if previous_grade < 60: recommendations.append("📚 Foundational knowledge might be weak. Check Digital Library.")
        except Exception as e:
            flash(f"Error during prediction: {str(e)}", "error")

    return render_template('predictor.html', 
                           points=points, 
                           prediction=prediction, 
                           recommendations=recommendations,
                           model_ready=(model is not None))

@app.route('/syllabus')
def syllabus():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    from src.syllabus_data import SYLLABUS_DATA, ADDITIONAL_SYLLABUS, SUBJECT_DETAILS
    return render_template('syllabus.html', 
                           syllabus=SYLLABUS_DATA, 
                           extras=ADDITIONAL_SYLLABUS, 
                           details=SUBJECT_DETAILS,
                           user_year=session.get('user_year'),
                           user_dept=session.get('user_department'))

@app.route('/library')
def library():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    subjects = pd.read_sql_query("SELECT id, name FROM subjects ORDER BY name ASC", conn).to_dict('records')
    conn.close()
    
    resources = get_resources().to_dict('records')
    return render_template('library.html', resources=resources, subjects=subjects)

@app.route('/api/library/add', methods=['POST'])
@staff_only
def api_add_resource_route():
    title = request.form.get('title')
    author = request.form.get('author')
    edition = request.form.get('edition', '')
    res_type = request.form.get('type')
    subject_id = request.form.get('subject_id')
    resource_url = request.form.get('resource_url', '')
    
    file_path = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            upload_dir = "uploads/resources"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{secrets.token_hex(4)}_{file.filename}")
            file.save(file_path)
            
    file_size = "0 MB"
    if file_path:
        try:
            file_size = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB"
        except:
            pass
            
    add_resource(subject_id, title, author, edition, file_path, file_size, res_type, session.get('user_id', 0), resource_url)
    add_activity_log(session.get('user_id'), 'UPLOAD', f'Uploaded resource: {title}', request.remote_addr)
    flash("Resource added successfully!", "success")
    return redirect(url_for('library'))

@app.route('/api/library/delete/<int:resource_id>', methods=['POST'])
@staff_only
def api_delete_resource(resource_id):
    delete_resource(resource_id)
    add_activity_log(session.get('user_id'), 'DELETE', f'Deleted resource ID {resource_id}', request.remote_addr)
    flash("Resource deleted successfully", "success")
    return redirect(url_for('library'))

@app.route('/api/library/update/<int:resource_id>', methods=['POST'])
@staff_only
def api_update_resource(resource_id):
    title = request.form.get('title')
    author = request.form.get('author')
    edition = request.form.get('edition')
    res_type = request.form.get('type')
    subject_id = request.form.get('subject_id')
    
    update_resource(resource_id, title, author, edition, res_type, subject_id)
    flash("Resource updated successfully", "success")
    return redirect(url_for('library'))

@app.route('/api/library/download/<int:resource_id>')
def api_download_resource(resource_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    res = conn.execute("SELECT file_path, title FROM resources WHERE id = ?", (resource_id,)).fetchone()
    conn.close()
    
    if res and os.path.exists(res[0]):
        track_download(session['user_id'], resource_id)
        return send_file(res[0], as_attachment=True)
    
    flash("Resource not found or file missing", "error")
    return redirect(url_for('library'))

@app.route('/guide')
def guide():
    return render_template('guide.html')

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return redirect(url_for('logout'))
    
    # Get system settings for admin
    from src.database import get_system_settings
    sys_settings = get_system_settings() if session.get('role') == 'Admin' else {}
        
    return render_template('settings.html', user=user_data, sys_settings=sys_settings)

@app.route('/api/settings/update', methods=['POST'])
def api_settings_update():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = request.form.get('username')
    email = request.form.get('email')
    
    if update_user_profile(session['user_id'], username, email):
        session['username'] = username # Update session username
        flash('Profile updated successfully!', 'success')
    else:
        flash('Error updating profile. Email or Username might already be in use.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/api/settings/change_password', methods=['POST'])
def api_settings_change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required.', 'error')
        return redirect(url_for('settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('settings'))
    
    if len(new_password) < 4:
        flash('Password must be at least 4 characters.', 'error')
        return redirect(url_for('settings'))
    
    # Verify current password
    from src.database import hash_password, get_db_connection
    conn = get_db_connection()
    stored = conn.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    if not stored or stored[0] != hash_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('settings'))
    
    # Update password
    if update_user_profile(session['user_id'], session['username'], None, new_password):
        flash('Password changed successfully!', 'success')
    else:
        flash('Error changing password.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/api/settings/system', methods=['POST'])
@admin_only
def api_settings_system():
    from src.database import update_system_setting
    
    update_system_setting('site_name', request.form.get('site_name', 'SMTEC EDUPREDICT'))
    update_system_setting('college_name', request.form.get('college_name', ''))
    update_system_setting('auto_approve', '1' if request.form.get('auto_approve') else '0')
    update_system_setting('allow_staff_uploads', '1' if request.form.get('allow_staff_uploads') else '0')
    update_system_setting('enable_leaderboard', '1' if request.form.get('enable_leaderboard') else '0')
    
    flash('System settings saved successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/api/settings/logout_all', methods=['POST'])
def api_settings_logout_all():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Clear session (Flask server-side session) — effectively logs out current device
    # For true multi-device logout, would need session store; this clears current + changes secret
    session.clear()
    flash('You have been logged out from all sessions.', 'success')
    return redirect(url_for('login'))

@app.route('/api/settings/delete', methods=['POST'])
def api_settings_delete():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    delete_user(session['user_id'])
    session.clear()
    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('login'))


# --- Student Hub Routes ---

@app.route('/student_hub')
def student_hub():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') in ['Staff', 'Admin']:
        flash("Staff members manage tasks from the Staff Portal.", "info")
        return redirect(url_for('staff_portal'))
    
    user_id = session['user_id']
    points = get_user_points(user_id)

    # Get student's year and department for filtering
    user_data = get_user_by_id(user_id)
    user_year = user_data[6] if user_data and len(user_data) > 6 else None
    user_dept = user_data[7] if user_data and len(user_data) > 7 else None

    # Filter all staff-uploaded data by student's year & department
    upcoming_exams = get_global_exams(year=user_year, department=user_dept)
    todos = get_todos(user_id)
    assigned_tasks = get_assigned_tasks_for_student(user_id, year=user_year, department=user_dept).to_dict('records')
    leaderboard = get_leaderboard(limit=5)

    # Study materials filtered by student's year & dept
    from src.database import get_resources
    resources = get_resources(year=user_year, department=user_dept).to_dict('records')

    # Question bank PDFs filtered by student's year & dept
    question_pdfs = get_question_pdfs(year=user_year, department=user_dept).to_dict('records')

    # Broadcasts for this student
    from src.database import get_broadcasts
    broadcasts = get_broadcasts(user_year, user_dept)
    
    from src.syllabus_data import SYLLABUS_DATA
    cse_first_year = {
        'Semester 1': SYLLABUS_DATA['Computer Science and Engineering (CSE)']['Semester 1'],
        'Semester 2': SYLLABUS_DATA['Computer Science and Engineering (CSE)']['Semester 2']
    }
    
    return render_template('student_hub.html', 
                           points=points, 
                           exams=upcoming_exams, 
                           todos=todos, 
                           assigned_tasks=assigned_tasks,
                           leaderboard=leaderboard,
                           resources=resources,
                           question_pdfs=question_pdfs,
                           cse_first_year=cse_first_year,
                           broadcasts=broadcasts)


@app.route('/staff/exams')
@staff_only
def staff_exams():
    """Staff exam schedule page - add/view/delete exams."""
    conn = get_db_connection()
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # Get subjects for dropdown
    subject_query = "SELECT id, name FROM subjects WHERE 1=1"
    sub_params = []
    if staff_dept:
        subject_query += " AND (department = ? OR department IS NULL OR department = '')"
        sub_params.append(staff_dept)
    if staff_year:
        subject_query += " AND (year = ? OR year IS NULL OR year = '')"
        sub_params.append(staff_year)
    subject_query += " ORDER BY name ASC"
    subjects = pd.read_sql_query(subject_query, conn, params=sub_params).to_dict('records')
    
    conn.close()
    
    # Get exams filtered by dept/year
    exams = get_global_exams(year=staff_year, department=staff_dept)
    
    return render_template('staff_exams.html',
                         subjects=subjects,
                         exams=exams,
                         staff_dept=staff_dept,
                         staff_year=staff_year)

@app.route('/api/add_exam', methods=['POST'])
@staff_only
def api_add_exam():
    data = request.form
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    add_global_exam(data.get('subject'), data.get('date'), year=staff_year, department=staff_dept)
    add_activity_log(session.get('user_id'), 'UPLOAD', f'Added exam: {data.get("subject")} on {data.get("date")}', request.remote_addr)
    flash('Exam added to schedule!', 'success')
    return redirect(url_for('staff_exams'))

@app.route('/api/delete_exam/<int:exam_id>', methods=['POST'])
@staff_only
def api_delete_exam(exam_id):
    delete_global_exam(exam_id)
    add_activity_log(session.get('user_id'), 'DELETE', f'Removed exam ID {exam_id} from schedule', request.remote_addr)
    flash('Exam removed from schedule!', 'success')
    return redirect(url_for('staff_exams'))

@app.route('/api/add_todo', methods=['POST'])
def api_add_todo():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    task = request.form.get('task')
    if task:
        add_todo(session['user_id'], task)
        flash('Task added!', 'success')
    return redirect(url_for('student_hub'))

@app.route('/api/toggle_todo/<int:todo_id>', methods=['POST'])
def api_toggle_todo(todo_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    # We need current status to toggle. In Streamlit it was toggle_todo(todo_id, current_status)
    # Let's get it from the form or just toggle it in the DB logic if possible.
    # Looking at database.py toggle_todo: toggle_todo(todo_id, current_status)
    # It seems we need to know the current status.
    conn = get_db_connection()
    todo = conn.execute("SELECT completed FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    
    if todo:
        is_now_complete = toggle_todo(todo_id, bool(todo[0]))
        if is_now_complete:
            update_points(session['user_id'], 5)
            flash('Task completed! +5 XP', 'success')
    
    return redirect(url_for('student_hub'))

@app.route('/api/toggle_assigned_task/<int:task_id>', methods=['POST'])
def api_toggle_assigned_task(task_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    is_now_complete = toggle_assigned_task_completion(task_id, user_id)
    if is_now_complete:
        update_points(user_id, 10)
        flash('Staff task completed! +10 XP', 'success')
    
    return redirect(url_for('student_hub'))

@app.route('/api/delete_todo/<int:todo_id>', methods=['POST'])
def api_delete_todo(todo_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    delete_todo(todo_id)
    return redirect(url_for('student_hub'))

@app.route('/api/update_points', methods=['POST'])
def api_update_points():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.json
    points = data.get('points', 0)
    update_points(session['user_id'], points)
    return jsonify({'status': 'success'})

# --- Staff Portal Routes ---

@app.route('/staff')
@staff_only
def staff_portal():
    """Main dashboard for staff."""
    conn = get_db_connection()
    student_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'Student'").fetchone()[0]
    subject_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    resource_count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    task_count = conn.execute("SELECT COUNT(*) FROM assigned_tasks").fetchone()[0]
    
    # Get some recent activity or overview data
    subjects = pd.read_sql_query("SELECT * FROM subjects", conn).to_dict('records')
    
    # Get pending submissions for grading
    query = """
        SELECT sa.id, u.username, q.question_text, sa.answer, q.correct_answer as sample_answer, sa.submitted_at
        FROM student_answers sa
        JOIN users u ON sa.user_id = u.id
        JOIN questions q ON sa.question_id = q.id
        WHERE q.type = 'Short Answer' AND sa.is_correct IS NULL
    """
    pending_submissions = pd.read_sql_query(query, conn).to_dict('records')
    
    resources = get_resources().to_dict('records')
    assigned_tasks = get_assigned_tasks_for_staff().to_dict('records')
    global_exams = get_global_exams()
    
    from src.database import get_all_students_engagement_list
    students = get_all_students_engagement_list().to_dict('records')
    
    # Get all topics for the question bank dropdown
    topics = pd.read_sql_query("SELECT id, title FROM topics ORDER BY title ASC", conn).to_dict('records')
    conn.close()
    
    question_pdfs = get_question_pdfs().to_dict('records')
    
    # Fetch broadcasts for staff
    from src.database import get_broadcasts
    broadcasts = get_broadcasts()
    
    return render_template('staff_portal.html', 
                           student_count=student_count,
                           subject_count=subject_count,
                           resource_count=resource_count,
                           task_count=task_count,
                           subjects=subjects, 
                           pending_submissions=pending_submissions,
                           resources=resources,
                           assigned_tasks=assigned_tasks,
                           global_exams=global_exams,
                           topics=topics,
                           students=students,
                           question_pdfs=question_pdfs,
                           broadcasts=broadcasts)

@app.route('/staff/student-view')
@staff_only
def staff_student_view():
    """Preview what students see — exams, marks, attendance, resources."""
    conn = get_db_connection()
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # 1. Exams for this dept/year
    exams = get_global_exams(year=staff_year, department=staff_dept)
    
    # 2. Internal marks uploaded for this dept/year students
    marks_query = """
        SELECT m.id, u.username as student_name, s.name as subject_name, 
               m.test_name, m.marks_obtained, m.total_marks, m.created_at
        FROM internal_marks m
        JOIN users u ON m.student_id = u.id
        JOIN subjects s ON m.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if staff_dept:
        marks_query += " AND u.department = ?"
        params.append(staff_dept)
    if staff_year:
        marks_query += " AND u.year = ?"
        params.append(staff_year)
    marks_query += " ORDER BY m.created_at DESC LIMIT 50"
    marks_data = pd.read_sql_query(marks_query, conn, params=params).to_dict('records')
    
    # 3. Attendance summary for this dept/year
    att_query = """
        SELECT a.date, 
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
               SUM(CASE WHEN a.status != 'Present' THEN 1 ELSE 0 END) as absent_count,
               COUNT(*) as total,
               s.name as subject_name
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE 1=1
    """
    att_params = []
    if staff_dept:
        att_query += " AND u.department = ?"
        att_params.append(staff_dept)
    if staff_year:
        att_query += " AND u.year = ?"
        att_params.append(staff_year)
    att_query += " GROUP BY a.date, a.subject_id ORDER BY a.date DESC LIMIT 30"
    attendance_summary = pd.read_sql_query(att_query, conn, params=att_params).to_dict('records')
    
    # 4. Resources
    from src.database import get_resources
    resources = get_resources().to_dict('records')
    
    # 5. Student count
    stu_query = "SELECT COUNT(*) FROM users WHERE role = 'Student'"
    stu_params = []
    if staff_dept:
        stu_query += " AND department = ?"
        stu_params.append(staff_dept)
    if staff_year:
        stu_query += " AND year = ?"
        stu_params.append(staff_year)
    student_count = conn.execute(stu_query, stu_params).fetchone()[0]
    
    conn.close()
    
    return render_template('staff_student_view.html',
                         exams=exams,
                         marks_data=marks_data,
                         attendance_summary=attendance_summary,
                         resources=resources,
                         student_count=student_count,
                         staff_dept=staff_dept,
                         staff_year=staff_year)

@app.route('/staff/marks', methods=['GET'])
@staff_only
def staff_marks():
    """Route for uploading/viewing student internal marks (Excel-style bulk entry)."""
    conn = get_db_connection()
    
    # Get staff's department and year from session/profile
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # Filter students by dept/year if staff has them set
    student_query = "SELECT id, username, email FROM users WHERE role = 'Student'"
    params = []
    if staff_dept:
        student_query += " AND department = ?"
        params.append(staff_dept)
    if staff_year:
        student_query += " AND year = ?"
        params.append(staff_year)
    student_query += " ORDER BY username ASC"
    
    students = pd.read_sql_query(student_query, conn, params=params).to_dict('records')
    
    # Get subjects filtered by dept/year
    subject_query = "SELECT id, name FROM subjects WHERE 1=1"
    sub_params = []
    if staff_dept:
        subject_query += " AND (department = ? OR department IS NULL OR department = '')"
        sub_params.append(staff_dept)
    if staff_year:
        subject_query += " AND (year = ? OR year IS NULL OR year = '')"
        sub_params.append(staff_year)
    subject_query += " ORDER BY name ASC"
    
    subjects = pd.read_sql_query(subject_query, conn, params=sub_params).to_dict('records')
    
    # Get departments and years for manual override (Admin)
    departments = [row[0] for row in conn.execute("SELECT name FROM departments ORDER BY name ASC").fetchall()]
    years = [row[0] for row in conn.execute("SELECT name FROM academic_years ORDER BY id ASC").fetchall()]
    
    marks_list = get_internal_marks().to_dict('records')
    conn.close()
    return render_template('staff_marks.html', 
                           students=students, 
                           subjects=subjects, 
                           marks_list=marks_list,
                           staff_dept=staff_dept,
                           staff_year=staff_year,
                           departments=departments,
                           years=years)

@app.route('/api/staff/get_subjects')
@staff_only
def api_get_subjects():
    """Returns subjects filtered by department and year."""
    dept = request.args.get('department', '')
    year = request.args.get('year', '')
    
    conn = get_db_connection()
    query = "SELECT id, name FROM subjects WHERE 1=1"
    params = []
    
    if dept:
        query += " AND (department = ? OR department IS NULL OR department = '')"
        params.append(dept)
    if year:
        query += " AND (year = ? OR year IS NULL OR year = '')"
        params.append(year)
    
    query += " ORDER BY name ASC"
    subjects = pd.read_sql_query(query, conn, params=params).to_dict('records')
    conn.close()
    
    return jsonify(subjects)

@app.route('/api/staff/get_students')
@staff_only
def api_get_students():
    """Returns students filtered by department and year."""
    dept = request.args.get('department', '')
    year = request.args.get('year', '')
    
    conn = get_db_connection()
    query = "SELECT id, username, email FROM users WHERE role = 'Student'"
    params = []
    
    if dept:
        query += " AND department = ?"
        params.append(dept)
    if year:
        query += " AND year = ?"
        params.append(year)
    
    query += " ORDER BY username ASC"
    students = pd.read_sql_query(query, conn, params=params).to_dict('records')
    conn.close()
    
    return jsonify(students)

@app.route('/api/staff/bulk_marks', methods=['POST'])
@staff_only
def api_bulk_marks():
    """Bulk upload marks for multiple students at once."""
    data = request.json
    subject_id = data.get('subject_id')
    test_name = data.get('test_name')
    total_marks = data.get('total_marks')
    marks_list = data.get('marks', [])
    absent_list = data.get('absent', [])
    
    if not subject_id or not test_name or not total_marks:
        return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400
    
    if not marks_list and not absent_list:
        return jsonify({'status': 'error', 'message': 'No marks or absent entries provided.'}), 400
    
    count = 0
    # Save marks entries
    for entry in marks_list:
        student_id = entry.get('student_id')
        marks = entry.get('marks')
        if student_id is not None and marks is not None:
            add_internal_mark(student_id, subject_id, test_name, marks, total_marks)
            count += 1
    
    # Save absent entries (marks = -1 as sentinel)
    absent_count = 0
    for entry in absent_list:
        student_id = entry.get('student_id')
        if student_id is not None:
            add_internal_mark(student_id, subject_id, test_name, -1, total_marks)
            absent_count += 1
    
    return jsonify({
        'status': 'success', 
        'count': count, 
        'absent_count': absent_count,
        'message': f'{count} marks + {absent_count} absent uploaded successfully!'
    })

@app.route('/api/staff/delete_mark/<int:mark_id>', methods=['DELETE'])
@staff_only
def api_delete_mark(mark_id):
    """Delete a single internal marks record."""
    delete_internal_mark(mark_id)
    return jsonify({'status': 'success', 'message': 'Record deleted.'})

@app.route('/api/staff/update_mark/<int:mark_id>', methods=['PUT'])
@staff_only
def api_update_mark(mark_id):
    """Update marks for a single record."""
    data = request.json
    new_marks = data.get('marks_obtained')
    if new_marks is None:
        return jsonify({'status': 'error', 'message': 'Missing marks value.'}), 400
    update_internal_mark(mark_id, new_marks)
    return jsonify({'status': 'success', 'message': 'Marks updated.'})


@app.route('/staff/attendance', methods=['GET'])
@staff_only
def staff_attendance():
    """Route for recording/viewing student attendance (Excel-style bulk entry)."""
    conn = get_db_connection()
    
    # Get staff's department and year from session
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # Filter students by dept/year
    student_query = "SELECT id, username, email FROM users WHERE role = 'Student'"
    params = []
    if staff_dept:
        student_query += " AND department = ?"
        params.append(staff_dept)
    if staff_year:
        student_query += " AND year = ?"
        params.append(staff_year)
    student_query += " ORDER BY username ASC"
    students = pd.read_sql_query(student_query, conn, params=params).to_dict('records')
    
    # Filter subjects by dept/year
    subject_query = "SELECT id, name FROM subjects WHERE 1=1"
    sub_params = []
    if staff_dept:
        subject_query += " AND (department = ? OR department IS NULL OR department = '')"
        sub_params.append(staff_dept)
    if staff_year:
        subject_query += " AND (year = ? OR year IS NULL OR year = '')"
        sub_params.append(staff_year)
    subject_query += " ORDER BY name ASC"
    subjects = pd.read_sql_query(subject_query, conn, params=sub_params).to_dict('records')
    
    # Get departments and years for filter dropdowns
    departments = [row[0] for row in conn.execute("SELECT name FROM departments ORDER BY name ASC").fetchall()]
    years = [row[0] for row in conn.execute("SELECT name FROM academic_years ORDER BY id ASC").fetchall()]
    
    attendance_data = get_attendance_report().to_dict('records')
    conn.close()
    
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    
    return render_template('staff_attendance.html', 
                         students=students, 
                         subjects=subjects, 
                         attendance_data=attendance_data,
                         today_date=today,
                         staff_dept=staff_dept,
                         staff_year=staff_year,
                         departments=departments,
                         years=years)

@app.route('/api/staff/bulk_attendance', methods=['POST'])
@staff_only
def api_bulk_attendance():
    """Bulk save attendance for all students at once."""
    data = request.json
    subject_id = data.get('subject_id')
    date_str = data.get('date')
    records = data.get('records', [])
    
    if not subject_id or not date_str or not records:
        return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400
    
    saved = []
    for rec in records:
        student_id = rec.get('student_id')
        status = rec.get('status', 'Absent')
        name = rec.get('name', '')
        if student_id:
            record_attendance(student_id, subject_id, date_str, status)
            saved.append({'name': name, 'student_id': student_id, 'status': status})
    
    return jsonify({'status': 'success', 'count': len(saved), 'records': saved})

@app.route('/api/staff/get_attendance')
@staff_only
def api_get_attendance():
    """Get attendance records. Supports filtering by subject_id, date, department, year."""
    subject_id = request.args.get('subject_id')
    date_str = request.args.get('date')
    dept = request.args.get('department', '')
    year = request.args.get('year', '')
    
    conn = get_db_connection()
    query = """
        SELECT a.id, u.id as student_id, u.username as name, a.status, a.date, s.name as subject_name
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE 1=1
    """
    params = []
    
    if subject_id:
        query += " AND a.subject_id = ?"
        params.append(subject_id)
    if date_str:
        query += " AND a.date = ?"
        params.append(date_str)
    if dept:
        query += " AND u.department = ?"
        params.append(dept)
    if year:
        query += " AND u.year = ?"
        params.append(year)
    
    query += " ORDER BY a.date DESC, u.username ASC"
    
    records = pd.read_sql_query(query, conn, params=params).to_dict('records')
    conn.close()
    
    return jsonify(records)

@app.route('/api/staff/update_attendance/<int:att_id>', methods=['PUT'])
@staff_only
def api_update_attendance(att_id):
    """Toggle attendance status for a single record."""
    data = request.json
    new_status = data.get('status')
    if not new_status:
        return jsonify({'status': 'error', 'message': 'Missing status.'}), 400
    update_attendance_status(att_id, new_status)
    return jsonify({'status': 'success', 'new_status': new_status})

@app.route('/api/staff/delete_attendance/<int:att_id>', methods=['DELETE'])
@staff_only
def api_delete_attendance(att_id):
    """Delete a single attendance record."""
    delete_attendance(att_id)
    return jsonify({'status': 'success', 'message': 'Record deleted.'})

@app.route('/staff/feedback')
@staff_only
def staff_feedback():
    """Route for viewing student feedback."""
    feedback_data = get_feedback_list().to_dict('records')
    return render_template('staff_feedback.html', feedback_data=feedback_data)

@app.route('/staff/assignments')
@staff_only
def staff_assignments():
    """Manage assignments - add/view/delete."""
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    assigned_tasks = get_assigned_tasks_for_staff().to_dict('records')
    
    return render_template('staff_assignments.html',
                         assigned_tasks=assigned_tasks,
                         staff_dept=staff_dept,
                         staff_year=staff_year)

@app.route('/staff/questions')
@staff_only
def staff_questions():
    """Manage question bank - add questions, upload PDFs."""
    conn = get_db_connection()
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # Get topics for dropdown
    topics = pd.read_sql_query("SELECT id, title FROM topics ORDER BY title ASC", conn).to_dict('records')
    
    # Get existing questions
    q_query = """
        SELECT q.id, q.question_text, q.type, q.correct_answer, q.points, t.title as topic_name
        FROM questions q
        JOIN topics t ON q.topic_id = t.id
        ORDER BY q.id DESC LIMIT 50
    """
    questions = pd.read_sql_query(q_query, conn).to_dict('records')
    conn.close()
    
    question_pdfs = get_question_pdfs().to_dict('records')
    
    return render_template('staff_questions.html',
                         topics=topics,
                         questions=questions,
                         question_pdfs=question_pdfs,
                         staff_dept=staff_dept,
                         staff_year=staff_year)

@app.route('/api/staff/add_subject', methods=['POST'])
@staff_only
def api_add_subject():
    name = request.form.get('name')
    desc = request.form.get('description')
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO subjects (name, description) VALUES (?, ?)", (name, desc))
        conn.commit()
        flash(f"Subject '{name}' added!", "success")
    except:
        flash("Error adding subject.", "error")
    finally:
        conn.close()
    return redirect(url_for('staff_portal') + '#subjects')

@app.route('/api/staff/add_unit', methods=['POST'])
@staff_only
def api_add_unit():
    subject_id = request.form.get('subject_id')
    title = request.form.get('title')
    conn = get_db_connection()
    conn.execute("INSERT INTO units (subject_id, title) VALUES (?, ?)", (subject_id, title))
    conn.commit()
    conn.close()
    flash(f"Unit '{title}' added!", "success")
    return redirect(url_for('staff_portal') + '#subjects')

@app.route('/api/staff/add_topic', methods=['POST'])
@staff_only
def api_add_topic():
    unit_id = request.form.get('unit_id')
    title = request.form.get('title')
    content = request.form.get('content')
    video_url = request.form.get('video_url')
    
    file_path = None
    if 'pdf' in request.files:
        pdf = request.files['pdf']
        if pdf.filename != '':
            os.makedirs('uploads', exist_ok=True)
            file_path = os.path.join('uploads', pdf.filename)
            pdf.save(file_path)
            
    conn = get_db_connection()
    conn.execute("INSERT INTO topics (unit_id, title, content, video_url, pdf_path) VALUES (?, ?, ?, ?, ?)",
                 (unit_id, title, content, video_url, file_path))
    conn.commit()
    
    # Notify students
    students = conn.execute("SELECT id FROM users WHERE role = 'Student'").fetchall()
    for (s_id,) in students:
        add_notification(s_id, f"📖 New Topic Added: {title}")
    
    conn.commit()
    conn.close()
    flash(f"Topic '{title}' added!", "success")
    return redirect(url_for('staff_portal', tab='subjects'))

@app.route('/api/staff/add_question', methods=['POST'])
@staff_only
def api_add_question():
    topic_id = request.form.get('topic_id')
    q_text = request.form.get('question_text')
    q_type = request.form.get('type')
    pts = request.form.get('points', 10)
    
    opt_json = None
    correct = request.form.get('correct_answer')
    
    if q_type == 'MCQ':
        opts = request.form.getlist('options[]')
        import json
        opt_json = json.dumps([o.strip() for o in opts if o.strip()])
        # correct index or value? Let's assume value for simplicity matching Streamlit logic
    
    q_link = request.form.get('link')
    
    # If text is empty, use link as placeholder
    if not q_text and q_link:
        q_text = "See external reference link"

    conn = get_db_connection()
    conn.execute("INSERT INTO questions (topic_id, question_text, type, options, correct_answer, points, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (topic_id, q_text, q_type, opt_json, correct, pts, q_link))
    conn.commit()
    conn.close()
    flash("Question added to bank!", "success")
    return redirect(url_for('staff_questions'))

@app.route('/api/staff/upload_question_pdf', methods=['POST'])
@staff_only
def api_upload_question_pdf():
    topic = request.form.get('topic')
    q_type = request.form.get('type')
    
    if 'pdf_file' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('staff_questions'))
        
    file = request.files['pdf_file']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('staff_questions'))
        
    if file and file.filename.endswith('.pdf'):
        upload_dir = "uploads/question_bank"
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = f"qb_{secrets.token_hex(4)}_{file.filename}".replace(" ", "_")
        filepath = os.path.join(upload_dir, safe_filename)
        file.save(filepath)
        
        add_question_pdf(topic, q_type, filepath)
        flash("Question Bank PDF uploaded successfully!", "success")
    else:
        flash("Invalid file type. Please upload a PDF.", "error")
        
    return redirect(url_for('staff_questions'))

@app.route('/api/staff/delete_question_pdf/<int:pdf_id>', methods=['POST'])
@staff_only
def api_delete_question_pdf(pdf_id):
    delete_question_pdf(pdf_id)
    flash("Question Bank PDF deleted.", "success")
    return redirect(url_for('staff_questions'))

@app.route('/api/staff/download_question_pdf/<int:pdf_id>')
@staff_only
def api_download_question_pdf(pdf_id):
    conn = get_db_connection()
    res = conn.execute("SELECT file_path, topic FROM question_bank WHERE id = ?", (pdf_id,)).fetchone()
    conn.close()
    
    if res and os.path.exists(res[0]):
        return send_file(res[0], as_attachment=True)
    
    flash("File not found.", "error")
    return redirect(url_for('staff_portal', tab='courses') + '#questions')

@app.route('/api/staff/upload_resource', methods=['POST'])
@staff_only
def api_upload_resource():
    title = request.form.get('title')
    author = request.form.get('author')
    edition = request.form.get('edition')
    subject_id = request.form.get('subject_id')
    res_type = request.form.get('type')
    
    res_url = request.form.get('resource_url')
    file_path = None
    file_size = "0 MB"
    
    if 'file' in request.files:
        f = request.files['file']
        if f.filename != '':
            lib_dir = "resources"
            os.makedirs(lib_dir, exist_ok=True)
            safe_filename = f"{res_type}_{f.filename}".replace(" ", "_")
            file_path = os.path.join(lib_dir, safe_filename)
            f.save(file_path)
            file_size = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB"
            
    if file_path or res_url:
        add_resource(subject_id, title, author, edition, file_path, file_size, res_type, session['user_id'], res_url)
        flash(f"Resource '{title}' added successfully!", "success")
    else:
        flash("Please provide either a file or a link.", "error")
            
    return redirect(url_for('staff_portal', tab='resources'))

@app.route('/api/staff/grade', methods=['POST'])
@staff_only
def api_grade_submission():
    submission_id = request.form.get('submission_id')
    score = int(request.form.get('score', 0))
    
    conn = get_db_connection()
    conn.execute("UPDATE student_answers SET score = ?, is_correct = 1 WHERE id = ?", (score, submission_id))
    
    # Update student points & notify
    student = conn.execute("SELECT user_id, question_id FROM student_answers WHERE id = ?", (submission_id,)).fetchone()
    if student:
        s_id, q_id = student
        update_points(s_id, score)
        q_text = conn.execute("SELECT question_text FROM questions WHERE id = ?", (q_id,)).fetchone()[0]
        add_notification(s_id, f"📝 Your submission for '{q_text[:20]}...' has been graded! Score: {score}/10")
    
    conn.commit()
    conn.close()
    flash("Grade submitted!", "success")
    return redirect(url_for('staff_portal') + '#grading')

@app.route('/api/staff/add_assigned_task', methods=['POST'])
@staff_only
def api_add_assigned_task():
    title = request.form.get('title')
    desc = request.form.get('description')
    due_date = request.form.get('due_date')
    task_url = request.form.get('task_url')

    # If title is missing, use the URL as the title
    if not title and task_url:
        title = task_url.split('/')[-1] if '/' in task_url else task_url
        if len(title) > 30: title = title[:27] + "..."
    
    file_path = None
    if 'document' in request.files:
        f = request.files['document']
        if f.filename != '':
            task_dir = "uploads/tasks"
            os.makedirs(task_dir, exist_ok=True)
            safe_filename = f"task_{secrets.token_hex(4)}_{f.filename}".replace(" ", "_")
            file_path = os.path.join(task_dir, safe_filename)
            f.save(file_path)
            
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    add_assigned_task(session['user_id'], title, desc, due_date, task_url, file_path, staff_year, staff_dept)
    
    # Notify students
    conn = get_db_connection()
    students = conn.execute("SELECT id FROM users WHERE role = 'Student'").fetchall()
    for (s_id,) in students:
        add_notification(s_id, f"📌 New Task Assigned: {title} (Due: {due_date})")
    conn.close()
    
    flash(f"Task '{title}' allocated to all students!", "success")
    return redirect(url_for('staff_assignments'))

@app.route('/api/staff/delete_assigned_task/<int:task_id>', methods=['POST'])
@staff_only
def api_delete_assigned_task(task_id):
    delete_assigned_task(task_id)
    flash("Assigned task deleted.", "success")
    return redirect(url_for('staff_assignments'))

@app.route('/api/tasks/view_doc/<int:task_id>')
def api_view_task_doc(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    task = conn.execute("SELECT file_path, title FROM assigned_tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    
    if task and task[0] and os.path.exists(task[0]):
        # Check if already viewed to prevent infinite XP
        conn = get_db_connection()
        viewed = conn.execute("SELECT viewed_at FROM student_task_completions WHERE task_id = ? AND student_id = ?", (task_id, user_id)).fetchone()
        conn.close()
        
        # Mark as viewed instead of complete to show up in "Opened" list for Staff
        from src.database import mark_task_viewed
        mark_task_viewed(task_id, user_id)
        
        if not viewed or not viewed[0]:
            update_points(user_id, 5)
            flash(f"Task '{task[1]}' material opened! +5 XP earned.", "success")
        else:
            flash(f"Viewing material for '{task[1]}'.", "info")
            
        return send_file(task[0], as_attachment=False)
    
    flash("Document not found.", "error")
    return redirect(url_for('student_hub'))

@app.route('/api/staff/task_stats/<int:task_id>')
@staff_only
def api_get_task_stats(task_id):
    df = get_task_completions(task_id)
    return jsonify(df.to_dict('records'))

@app.route('/api/tasks/mark_viewed/<int:task_id>', methods=['POST'])
def api_mark_task_viewed(task_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    from src.database import mark_task_viewed
    mark_task_viewed(task_id, session['user_id'])
    return jsonify({'status': 'success'})

@app.route('/student_monitoring')
@staff_only
def student_monitoring():
    from src.database import get_all_students_engagement_list
    
    # Get staff's department and year from session
    staff_dept = session.get('user_department', '')
    staff_year = session.get('user_year', '')
    
    # Filter students by staff's dept/year
    students = get_all_students_engagement_list(year=staff_year or None, department=staff_dept or None).to_dict('records')
    
    # Get departments and years for filter dropdowns
    conn = get_db_connection()
    departments = [row[0] for row in conn.execute("SELECT name FROM departments ORDER BY name ASC").fetchall()]
    years = [row[0] for row in conn.execute("SELECT name FROM academic_years ORDER BY id ASC").fetchall()]
    conn.close()
    
    return render_template('student_details.html', 
                           students=students,
                           staff_dept=staff_dept,
                           staff_year=staff_year,
                           departments=departments,
                           years=years)

@app.route('/api/staff/get_engagement')
@staff_only
def api_get_engagement():
    """Returns full student engagement list filtered by department and year."""
    from src.database import get_all_students_engagement_list
    dept = request.args.get('department', '')
    year = request.args.get('year', '')
    
    students = get_all_students_engagement_list(
        year=year or None, 
        department=dept or None
    ).to_dict('records')
    
    return jsonify(students)

@app.route('/api/staff/student_stats/<int:student_id>')
@staff_only
def api_get_student_stats(student_id):
    from src.database import get_student_task_details
    df = get_student_task_details(student_id)
    return jsonify(df.to_dict('records'))

# --- GPA Calculator Route ---

@app.route('/gpa')
def gpa_calculator():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('gpa_calculator.html', syllabus=SYLLABUS_DATA)

# --- Learning Center Routes ---

@app.route('/learning')
def learning():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    subjects = pd.read_sql_query("SELECT * FROM subjects", conn).to_dict('records')
    conn.close()
    return render_template('learning_subjects.html', subjects=subjects)

@app.route('/learning/subject/<int:subject_id>')
def learning_subject(subject_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    subject = pd.read_sql_query("SELECT * FROM subjects WHERE id = ?", conn, params=(subject_id,)).iloc[0].to_dict()
    units = pd.read_sql_query("SELECT * FROM units WHERE subject_id = ? ORDER BY order_index", conn, params=(subject_id,)).to_dict('records')
    
    # Enrich units with topics
    for unit in units:
        unit['topics'] = pd.read_sql_query("SELECT * FROM topics WHERE unit_id = ? ORDER BY order_index", conn, params=(unit['id'],)).to_dict('records')
        
    conn.close()
    return render_template('learning_subject_view.html', subject=subject, units=units)

@app.route('/learning/topic/<int:topic_id>')
def learning_topic(topic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    topic = pd.read_sql_query("SELECT * FROM topics WHERE id = ?", conn, params=(topic_id,)).iloc[0].to_dict()
    
    # Get Unit and Subject info for breadcrumbs
    unit = pd.read_sql_query("SELECT * FROM units WHERE id = ?", conn, params=(topic['unit_id'],)).iloc[0].to_dict()
    subject = pd.read_sql_query("SELECT * FROM subjects WHERE id = ?", conn, params=(unit['subject_id'],)).iloc[0].to_dict()
    
    # Get notes
    note = get_topic_note(user_id, topic_id)
    
    # Get questions
    questions = pd.read_sql_query("SELECT * FROM questions WHERE topic_id = ?", conn, params=(topic_id,)).to_dict('records')
    for q in questions:
        if q['type'] == 'MCQ':
            import json
            q['options'] = json.loads(q['options'])
            
    # Get discussions
    discussions = get_discussions(topic_id)
    
    conn.close()
    return render_template('learning_topic_view.html', 
                           topic=topic, unit=unit, subject=subject, 
                           note=note, questions=questions, discussions=discussions)

@app.route('/api/save_note', methods=['POST'])
def api_save_note():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.json
    save_topic_note(session['user_id'], data['topic_id'], data['content'])
    return jsonify({'status': 'success'})

@app.route('/api/submit_quiz', methods=['POST'])
def api_submit_quiz():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.json
    user_id = session['user_id']
    q_id = data['question_id']
    answer = data['answer']
    task_id = data.get('task_id')
    
    conn = get_db_connection()
    q = pd.read_sql_query("SELECT * FROM questions WHERE id = ?", conn, params=(q_id,)).iloc[0]
    
    is_correct = None
    score = 0
    
    if q['type'] == 'MCQ':
        is_correct = (answer == q['correct_answer'])
        score = q['points'] if is_correct else 0
        if is_correct:
            update_points(user_id, score)
    else:
        # Short Answer: Manual grading
        # Notify staff
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE role IN ('Staff', 'Admin')")
        staff = c.fetchall()
        for (s_id,) in staff:
            add_notification(s_id, f"📥 New Submission: {session['username']} submitted a short answer for topic ID {q['topic_id']}")
    
    c = conn.cursor()
    c.execute("INSERT INTO student_answers (user_id, question_id, answer, is_correct, score) VALUES (?, ?, ?, ?, ?)",
              (user_id, q_id, answer, is_correct, score))
    conn.commit()
    conn.close()

    if task_id:
        newly_done = mark_assigned_task_complete(int(task_id), user_id)
        if newly_done:
            update_points(user_id, 10)
    
    return jsonify({
        'status': 'success', 
        'is_correct': is_correct, 
        'score': score,
        'correct_answer': q['correct_answer'] if q['type'] == 'MCQ' else None
    })

@app.route('/api/post_discussion', methods=['POST'])
def api_post_discussion():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.json
    add_discussion(data['topic_id'], session['user_id'], data['comment'])
    return jsonify({'status': 'success'})

@app.route('/api/mark_complete/<int:topic_id>', methods=['POST'])
def api_mark_complete(topic_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    task_id = request.args.get('task_id')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO student_progress (user_id, topic_id, completed, completed_at) VALUES (?, ?, 1, CURRENT_TIMESTAMP)", (user_id, topic_id))
    conn.commit()
    conn.close()
    
    if task_id:
        newly_done = mark_assigned_task_complete(int(task_id), user_id)
        if newly_done:
            update_points(user_id, 10)
        
    return jsonify({'status': 'success'})

# Predictor logic moved to line 199

@app.route('/api/predict', methods=['POST'])
def api_predict():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    import joblib
    import pandas as pd
    try:
        data = request.json
        model = joblib.load('models/student_performance_model.pkl')
        scaler = joblib.load('models/scaler.pkl')
        
        features = [
            float(data.get('study_hours', 5)),
            float(data.get('attendance', 85)),
            float(data.get('sleep_hours', 7)),
            float(data.get('participation', 60)),
            float(data.get('previous_grade', 75)),
            float(data.get('points', 0))
        ]
        
        # Engineering
        eng_score = (features[1] * 0.6) + (features[3] * 0.4)
        stud_ratio = features[0] / (features[2] + 0.1)
        full_features = features + [eng_score, stud_ratio]
        
        X = pd.DataFrame([full_features])
        X_scaled = scaler.transform(X)
        pred_val = float(model.predict(X_scaled)[0])
        
        recommendations = []
        if features[1] < 80: recommendations.append("Low attendance detected.")
        if pred_val < 50: recommendations.append("High risk of failure identified.")
        
        return jsonify({
            'status': 'success',
            'prediction': round(pred_val, 1),
            'recommendations': recommendations
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Student Feedback Route ---

@app.route('/feedback', methods=['GET', 'POST'])
def student_feedback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if not subject_id or not rating or not comment:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('student_feedback'))
        
        from src.database import add_feedback
        add_feedback(session['user_id'], int(subject_id), int(rating), comment)
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('student_feedback'))
    
    conn = get_db_connection()
    subjects = pd.read_sql_query("SELECT id, name FROM subjects", conn).to_dict('records')
    conn.close()
    return render_template('student_feedback.html', subjects=subjects)

# --- Admin Portal ---

@app.route('/admin/hub')
@admin_only
def admin_portal():
    import json
    from src.database import get_managed_users
    users = get_managed_users()
    
    # Dashboard Statistics
    stats = {
        'total': len(users),
        'pending': len([u for u in users if u.get('is_approved') == 0]),
        'students': len([u for u in users if u.get('role') == 'Student']),
        'staff': len([u for u in users if u.get('role') == 'Staff']),
        'admins': len([u for u in users if u.get('role') == 'Admin'])
    }
    
    # JSON for stat card drill-down (all users including current admin)
    all_users_json = json.dumps(users)
    
    # Fetch all broadcasts for admin to see + manage
    from src.database import get_broadcasts
    broadcasts = get_broadcasts()
    
    # Fetch system logs
    logs = get_all_activity_logs(limit=100).to_dict('records')
    
    # Filter out current admin so they don't delete themselves (for User Control tab)
    users = [u for u in users if u.get('id') != session['user_id']]
    return render_template('admin_portal.html', users=users, stats=stats, all_users_json=all_users_json, broadcasts=broadcasts, logs=logs)

@app.route('/api/admin/user_action', methods=['POST'])
@admin_only
def api_admin_action():
    action = request.form.get('action')
    user_id = request.form.get('user_id')
    
    if not action or not user_id:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
        
    user_id = int(user_id)
    from src.database import approve_user, reject_user, change_user_role
    
    try:
        if action == 'approve':
            approve_user(user_id)
            add_activity_log(session['user_id'], 'APPROVE', f'Admin approved user ID {user_id}', request.remote_addr)
            flash('User approved successfully.', 'success')
        elif action == 'reject':
            reject_user(user_id)
            add_activity_log(session['user_id'], 'DELETE', f'Admin deleted user ID {user_id}', request.remote_addr)
            flash('User rejected/deleted.', 'success')
        elif action.startswith('role_'):
            new_role = action.split('_')[1]
            change_user_role(user_id, new_role)
            add_activity_log(session['user_id'], 'ROLE_CHANGE', f'Changed user ID {user_id} role to {new_role}', request.remote_addr)
            flash(f'User role updated to {new_role}.', 'success')
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Centralized Curriculum Hub ---

@app.route('/curriculum')
def curriculum():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from src.database import get_global_exams, get_resources
    exams = get_global_exams()
    resources = get_resources().to_dict('records')
    
    return render_template('curriculum.html', exams=exams, resources=resources)

# --- Broadcast Routes ---

@app.route('/api/admin/send_broadcast', methods=['POST'])
@admin_only
def send_broadcast():
    from src.database import add_broadcast
    message = request.form.get('message', '').strip()
    year = request.form.get('year', 'all')
    department = request.form.get('department', 'all')
    
    if not message:
        flash('Broadcast message cannot be empty.', 'error')
        return redirect(url_for('admin_portal'))
    
    add_broadcast(message, year, department)
    add_activity_log(session['user_id'], 'BROADCAST', f'Sent broadcast: {message[:50]}...', request.remote_addr)
    flash('Broadcast sent successfully!', 'success')
    return redirect(url_for('admin_portal'))

@app.route('/api/admin/delete_broadcast/<int:broadcast_id>', methods=['POST'])
@admin_only
def api_delete_broadcast(broadcast_id):
    from src.database import delete_broadcast
    delete_broadcast(broadcast_id)
    flash('Broadcast deleted.', 'success')
    return redirect(url_for('admin_portal'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
