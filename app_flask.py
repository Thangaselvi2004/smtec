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
    add_internal_mark, get_internal_marks, record_attendance, get_attendance_report,
    add_feedback, get_feedback_list,
    add_global_exam, get_global_exams, delete_global_exam, get_pending_task_count,
    mark_assigned_task_complete, get_user_by_id, update_user_profile, delete_user, change_user_role, update_password_by_email,
    add_question_pdf, get_question_pdfs, delete_question_pdf
)
from src.auth import login_user, register_user
from src.syllabus_data import SYLLABUS_DATA

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Mock AI Interview Data
INTERVIEW_DATA = {
    "Software Engineer": [
        "Explain the concept of time complexity (Big O notation).",
        "What is the difference between a process and a thread?",
        "How does a hash map work internally?",
        "Describe a challenging bug you fixed and how you approached it."
    ],
    "Data Analyst": [
        "What is the difference between supervised and unsupervised learning?",
        "How do you handle missing data in a dataset?",
        "Explain the concept of p-value.",
        "What is SQL injection and how do you prevent it?"
    ],
    "HR/Behavioral": [
        "Tell me about yourself.",
        "What is your greatest strength and weakness?",
        "Describe a time you had a conflict with a team member.",
        "Where do you see yourself in 5 years?"
    ]
}

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
            
    add_resource(title, author, edition, res_type, subject_id, file_path, resource_url)
    flash("Resource added successfully!", "success")
    return redirect(url_for('library'))

@app.route('/api/library/delete/<int:resource_id>', methods=['POST'])
@staff_only
def api_delete_resource(resource_id):
    delete_resource(resource_id)
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
        
    return render_template('settings.html', user=user_data)

@app.route('/api/settings/update', methods=['POST'])
def api_settings_update():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Filter empty password
    password = password if password and len(password.strip()) > 0 else None
    
    if update_user_profile(session['user_id'], username, email, password):
        session['username'] = username # Update session username
        flash('Profile updated successfully!', 'success')
    else:
        flash('Error updating profile. Email or Username might already be in use.', 'error')
    
    return redirect(url_for('settings'))

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
    upcoming_exams = get_global_exams()
    todos = get_todos(user_id)
    assigned_tasks = get_assigned_tasks_for_student(user_id).to_dict('records')
    leaderboard = get_leaderboard(limit=5)
    
    # Fetch study materials (resources)
    from src.database import get_resources
    resources = get_resources().to_dict('records')
    
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
                           cse_first_year=cse_first_year)

@app.route('/api/add_exam', methods=['POST'])
@staff_only
def api_add_exam():
    data = request.form
    add_global_exam(data.get('subject'), data.get('date'))
    flash('Exam added to global schedule!', 'success')
    return redirect(url_for('staff_portal') + '#exams')

@app.route('/api/delete_exam/<int:exam_id>', methods=['POST'])
@staff_only
def api_delete_exam(exam_id):
    delete_global_exam(exam_id)
    flash('Exam removed from global schedule!', 'success')
    return redirect(url_for('staff_portal') + '#exams')

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
                           question_pdfs=question_pdfs)

@app.route('/staff/marks', methods=['GET', 'POST'])
@staff_only
def staff_marks():
    """Route for uploading/viewing student internal marks."""
    conn = get_db_connection()
    students = pd.read_sql_query("SELECT id, username FROM users WHERE role = 'Student' ORDER BY username ASC", conn).to_dict('records')
    subjects = pd.read_sql_query("SELECT id, name FROM subjects ORDER BY name ASC", conn).to_dict('records')
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject_id = request.form.get('subject_id')
        test_name = request.form.get('test_name')
        marks = request.form.get('marks')
        total = request.form.get('total')
        
        if student_id and subject_id and test_name and marks and total:
            add_internal_mark(student_id, subject_id, test_name, marks, total)
            flash(f"Marks for {test_name} uploaded successfully!", "success")
        else:
            flash("All fields are required.", "error")
        return redirect(url_for('staff_marks'))
        
    marks_list = get_internal_marks().to_dict('records')
    conn.close()
    return render_template('staff_marks.html', students=students, subjects=subjects, marks_list=marks_list)

@app.route('/staff/attendance', methods=['GET', 'POST'])
@staff_only
def staff_attendance():
    """Route for recording/viewing student attendance."""
    conn = get_db_connection()
    students = pd.read_sql_query("SELECT id, username FROM users WHERE role = 'Student' ORDER BY username ASC", conn).to_dict('records')
    subjects = pd.read_sql_query("SELECT id, name FROM subjects ORDER BY name ASC", conn).to_dict('records')
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        date = request.form.get('date')
        
        if subject_id and date:
            for student in students:
                status = request.form.get(f"status_{student['id']}")
                if status:
                    record_attendance(student['id'], subject_id, date, status)
            flash(f"Attendance for {date} recorded successfully!", "success")
        else:
            flash("Please select a subject and date.", "error")
        return redirect(url_for('staff_attendance'))
    
    attendance_data = get_attendance_report().to_dict('records')
    conn.close()
    
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    
    return render_template('staff_attendance.html', 
                         students=students, 
                         subjects=subjects, 
                         attendance_data=attendance_data,
                         today_date=today)

@app.route('/staff/feedback')
@staff_only
def staff_feedback():
    """Route for viewing student feedback."""
    feedback_data = get_feedback_list().to_dict('records')
    return render_template('staff_feedback.html', feedback_data=feedback_data)

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
    return redirect(url_for('staff_portal', tab='courses') + '#questions')

@app.route('/api/staff/upload_question_pdf', methods=['POST'])
@staff_only
def api_upload_question_pdf():
    topic = request.form.get('topic')
    q_type = request.form.get('type')
    
    if 'pdf_file' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('staff_portal', tab='courses') + '#questions')
        
    file = request.files['pdf_file']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('staff_portal', tab='courses') + '#questions')
        
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
        
    return redirect(url_for('staff_portal', tab='courses') + '#questions')

@app.route('/api/staff/delete_question_pdf/<int:pdf_id>', methods=['POST'])
@staff_only
def api_delete_question_pdf(pdf_id):
    delete_question_pdf(pdf_id)
    flash("Question Bank PDF deleted.", "success")
    return redirect(url_for('staff_portal', tab='courses') + '#questions')

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
    
    add_assigned_task(session['user_id'], title, desc, due_date, task_url, file_path)
    
    # Notify students
    conn = get_db_connection()
    students = conn.execute("SELECT id FROM users WHERE role = 'Student'").fetchall()
    for (s_id,) in students:
        add_notification(s_id, f"📌 New Task Assigned: {title} (Due: {due_date})")
    conn.close()
    
    flash(f"Task '{title}' allocated to all students!", "success")
    return redirect(url_for('staff_portal') + '#tasks')

@app.route('/api/staff/delete_assigned_task/<int:task_id>', methods=['POST'])
@staff_only
def api_delete_assigned_task(task_id):
    delete_assigned_task(task_id)
    flash("Assigned task deleted.", "success")
    return redirect(url_for('staff_portal', tab='tasks'))

@app.route('/api/tasks/view_doc/<int:task_id>')
def api_view_task_doc(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    task = conn.execute("SELECT file_path, title FROM assigned_tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    
    if task and task[0] and os.path.exists(task[0]):
        # Auto-complete task
        newly_done = mark_assigned_task_complete(task_id, user_id)
        if newly_done:
            update_points(user_id, 10)
            flash(f"Task '{task[1]}' material viewed! +10 XP earned.", "success")
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
    students = get_all_students_engagement_list().to_dict('records')
    return render_template('student_details.html', students=students)

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
    from src.database import get_managed_users
    users = get_managed_users()
    
    # Dashboard Statistics
    stats = {
        'total': len(users),
        'pending': len([u for u in users if u[4] == 0]),
        'students': len([u for u in users if u[3] == 'Student']),
        'staff': len([u for u in users if u[3] == 'Staff']),
        'admins': len([u for u in users if u[3] == 'Admin'])
    }
    
    # Filter out current admin so they don't delete themselves
    users = [u for u in users if u[0] != session['user_id']]
    return render_template('admin_portal.html', users=users, stats=stats)

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
            flash('User approved successfully.', 'success')
        elif action == 'reject':
            reject_user(user_id)
            flash('User rejected/deleted.', 'success')
        elif action.startswith('role_'):
            new_role = action.split('_')[1]
            change_user_role(user_id, new_role)
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
