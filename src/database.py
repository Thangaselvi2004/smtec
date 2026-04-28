import sqlite3
import hashlib
import os

DB_NAME = "student.db"

def get_db_connection():
    """Helper to get a database connection with Row factory."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with users and user_data tables."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Student',
            points INTEGER DEFAULT 0,
            year TEXT,
            department TEXT
        )
    ''')
    
    # Check for role column (migration)
    try:
        c.execute('SELECT role FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Student'")
        # Make the first registered user an Admin if desired, or manually via DB.
    
    # Check if points column exists (for migration)
    try:
        c.execute('SELECT points FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0')
 
    # Check for email column (migration)
    try:
        c.execute('SELECT email FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN email TEXT')
        # Seed existing admin email
        c.execute("UPDATE users SET email = 'admin@portal.com' WHERE username = 'admin'")
    
    # Check for is_approved column (migration)
    try:
        c.execute('SELECT is_approved FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 0')
        # Existing users and admins should be auto-approved
        c.execute('UPDATE users SET is_approved = 1')

    # Check for is_blocked, last_login, status in users (migration)
    try:
        c.execute('SELECT is_blocked FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0')
        c.execute('ALTER TABLE users ADD COLUMN last_login TIMESTAMP')
        c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Active'")

    # Departments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Academic Years table
    c.execute('''
        CREATE TABLE IF NOT EXISTS academic_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Activity Logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # System Settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT
        )
    ''')

    # Announcements table
    c.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT NOT NULL,
            target_role TEXT DEFAULT 'All',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed default settings
    c.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('site_name', 'EduPredict Portal')")
    c.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('theme', 'dark')")
    
    # Seed default years/depts if empty
    c.execute("SELECT COUNT(*) FROM academic_years")
    if c.fetchone()[0] == 0:
        for y in ['1st Year', '2nd Year', '3rd Year', 'Final Year']:
            c.execute("INSERT INTO academic_years (name) VALUES (?)", (y,))
            
    c.execute("SELECT COUNT(*) FROM departments")
    if c.fetchone()[0] == 0:
        for d in ['CSE', 'ECE', 'MECH', 'IT', 'EEE', 'CIVIL', 'AIDS']:
            c.execute("INSERT INTO departments (name) VALUES (?)", (d,))
    
    # Subjects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')

    # Units table
    c.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')

    # Topics table
    c.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            video_url TEXT,
            pdf_path TEXT,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (unit_id) REFERENCES units (id)
        )
    ''')

    # Questions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            type TEXT NOT NULL, -- 'MCQ' or 'Short'
            options TEXT, -- JSON string for MCQ options
            correct_answer TEXT NOT NULL, 
            points INTEGER DEFAULT 10,
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        )
    ''')

    # Student Progress table
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            completed BOOLEAN DEFAULT 0,
            completed_at TIMESTAMP,
            UNIQUE(user_id, topic_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        )
    ''')

    # Student Answers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            is_correct BOOLEAN,
            score INTEGER DEFAULT 0,
            graded_by INTEGER, -- Staff user_id if manual
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (graded_by) REFERENCES users (id)
        )
    ''')

    # Notifications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Discussions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS discussions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            parent_id INTEGER, -- For nested replies
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES topics (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (parent_id) REFERENCES discussions (id)
        )
    ''')
    
    # Create user_data table (original, keep for compatibility)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create exams table (Staff uploaded schedule)
    c.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            subject TEXT,
            exam_date TEXT,
            description TEXT,
            file_path TEXT,
            year TEXT,
            department TEXT
        )
    ''')

    # Create todos table (original, keep)
    c.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Resource Hub Tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            title TEXT NOT NULL,
            author TEXT,
            edition TEXT,
            file_path TEXT NOT NULL,
            file_size TEXT,
            type TEXT, -- 'Book', 'Notes', 'Manual'
            uploader_id INTEGER,
            is_recommended BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploader_id) REFERENCES users (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (resource_id) REFERENCES resources (id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            UNIQUE(user_id, resource_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (resource_id) REFERENCES resources (id)
        )
    ''')
    
    # Create assigned_tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assigned_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            title TEXT,
            description TEXT,
            due_date TEXT,
            task_url TEXT,
            file_path TEXT,
            year TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES users(id)
        )
    ''')
    
    # Create student_task_completions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_task_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            viewed_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES assigned_tasks (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')

    # Create topic_notes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS topic_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, topic_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        )
    ''')

    # Migration: Add task_url column if it doesn't exist
    try:
        c.execute('SELECT task_url FROM assigned_tasks LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE assigned_tasks ADD COLUMN task_url TEXT')
    
    # Migration: Add viewed_at to student_task_completions
    try:
        c.execute('SELECT viewed_at FROM student_task_completions LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE student_task_completions ADD COLUMN viewed_at TIMESTAMP')

    # Migration: Add link to questions
    try:
        c.execute('SELECT link FROM questions LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE questions ADD COLUMN link TEXT')

    # Migration: Add resource_url to resources
    try:
        c.execute('SELECT resource_url FROM resources LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE resources ADD COLUMN resource_url TEXT')

    # Migration: Add file_path to assigned_tasks
    try:
        c.execute('SELECT file_path FROM assigned_tasks LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE assigned_tasks ADD COLUMN file_path TEXT')

    # Create global_exams table
    c.execute('''
        CREATE TABLE IF NOT EXISTS global_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            exam_date DATE NOT NULL
        )
    ''')
    
    # Create internal_marks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS internal_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            marks_obtained REAL,
            total_marks REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')
    
    # Create attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT NOT NULL, -- 'Present', 'Absent'
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')
    
    # Create feedback table
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')

    # Create question_bank (PDFs) table
    c.execute('''
        CREATE TABLE IF NOT EXISTS question_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            type TEXT,
            file_path TEXT,
            year TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create assignments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            title TEXT,
            description TEXT,
            year TEXT,
            department TEXT,
            file_path TEXT,
            task_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES users(id)
        )
    ''')

    # Create student_activity table
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            assignment_id INTEGER NOT NULL,
            status TEXT DEFAULT 'viewed', -- 'viewed', 'completed'
            marks INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, assignment_id),
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (assignment_id) REFERENCES assignments (id)
        )
    ''')

    # Migration: Add columns to student_activity if missing
    try:
        c.execute('SELECT submitted_at FROM student_activity LIMIT 1')
    except sqlite3.OperationalError:
        try: c.execute('ALTER TABLE student_activity ADD COLUMN submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except: pass
    
    try:
        c.execute('SELECT xp FROM student_activity LIMIT 1')
    except sqlite3.OperationalError:
        try: c.execute('ALTER TABLE student_activity ADD COLUMN xp INTEGER DEFAULT 0')
        except: pass
    
    try:
        c.execute('SELECT marks FROM student_activity LIMIT 1')
    except sqlite3.OperationalError:
        try: c.execute('ALTER TABLE student_activity ADD COLUMN marks INTEGER DEFAULT 0')
        except: pass

    # Migration: Add xp column to users if it doesn't exist
    try:
        c.execute('SELECT xp FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0')

    conn.commit()
    conn.close()

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, role='Student', email=None):
    """Adds a new user to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    try:
        c.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', 
                  (username, email, hashed_pw, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username or Email already exists
    finally:
        conn.close()

def check_user(identifier, password):
    """Checks if email (or username) and password match. Returns (id, username, role, is_approved)."""
    conn = get_db_connection()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    # Check email first, then fallback to username for legacy support
    c.execute('SELECT id, username, role, is_approved FROM users WHERE (email = ? OR username = ?) AND password = ?', 
              (identifier, identifier, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Fetch user details by ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, email, role, points, xp, year, department FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def update_user_profile(user_id, username, email, password=None):
    """Updates user profile information."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if password:
            hashed_pw = hash_password(password)
            c.execute('UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?', 
                      (username, email, hashed_pw, user_id))
        else:
            c.execute('UPDATE users SET username = ?, email = ? WHERE id = ?', 
                      (username, email, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username or email already exists
    finally:
        conn.close()

def update_user_class_details(user_id, year, department):
    """Updates user year and department."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET year = ?, department = ? WHERE id = ?', (year, department, user_id))
    conn.commit()
    conn.close()

def update_password_by_email(email, password):
    """Updates the password for a user given their email address."""
    conn = get_db_connection()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    c.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_pw, email))
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def approve_user(user_id):
    """Approves a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def reject_user(user_id):
    """Deletes/Rejects a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def change_user_role(user_id, role):
    """Updates a user's role."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
    conn.commit()
    conn.close()

def update_user_class_details(user_id, year, department):
    """Persists year and department to the users table."""
    conn = get_db_connection()
    c = conn.cursor()
    # Add columns if they don't exist
    try:
        c.execute('ALTER TABLE users ADD COLUMN year TEXT')
    except:
        pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN department TEXT')
    except:
        pass
    c.execute('UPDATE users SET year = ?, department = ? WHERE id = ?', (year, department, user_id))
    conn.commit()
    conn.close()


def get_managed_users():
    """Retrieves all registered users for admin approval and role management."""
    import pandas as pd
    conn = get_db_connection()
    # Using pandas for easy dict conversion or fetching as dicts
    query = 'SELECT id, username, email, role, is_approved, last_login, is_blocked, status FROM users ORDER BY is_approved ASC, username ASC'
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.to_dict('records')

def add_data(user_id, content):
    """Adds a data entry for a specific user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO user_data (user_id, content) VALUES (?, ?)', (user_id, content))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """Retrieves all data for a specific user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, content, created_at FROM user_data WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def update_data(data_id, new_content):
    """Updates a specific data entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE user_data SET content = ? WHERE id = ?', (new_content, data_id))
    conn.commit()
    conn.close()

def delete_question_pdf(pdf_id):
    """Deletes a question bank PDF and its file."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT file_path FROM question_bank WHERE id = ?", (pdf_id,))
    res = c.fetchone()
    if res and res[0]:
        abs_path = os.path.join('static', res[0])
        if os.path.exists(abs_path):
            try: os.remove(abs_path)
            except: pass
            
    c.execute("DELETE FROM question_bank WHERE id = ?", (pdf_id,))
    conn.commit()
    conn.close()

def delete_data(data_id):
    """Deletes a specific data entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM user_data WHERE id = ?', (data_id,))
    conn.commit()
    conn.close()

def get_user_points(user_id):
    """Retrieves current points for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_points(user_id, points):
    """Updates user points (add/subtract)."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET points = points + ? WHERE id = ?', (points, user_id))
    conn.commit()
    conn.close()

def add_subject(name, description=""):
    """Adds a new subject."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO subjects (name, description) VALUES (?, ?)', (name, description))
    conn.commit()
    conn.close()

def add_unit(subject_id, title):
    """Adds a new unit to a subject."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO units (subject_id, title) VALUES (?, ?)', (subject_id, title))
    conn.commit()
    conn.close()

def add_question(topic_id, question_text, q_type, options=None, correct_answer='N/A'):
    """Adds a new question to the question bank."""
    import json
    conn = get_db_connection()
    c = conn.cursor()
    options_json = json.dumps(options) if options else None
    c.execute('INSERT INTO questions (topic_id, question_text, type, options, correct_answer) VALUES (?, ?, ?, ?, ?)', 
              (topic_id, question_text, q_type, options_json, correct_answer))
    conn.commit()
    conn.close()

def add_exam(title, subject, exam_date, description, file_path, year, department):
    """Adds a new exam schedule entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO exams (title, subject, exam_date, description, file_path, year, department)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, subject, exam_date, description, file_path, year, department))
    conn.commit()
    conn.close()

def get_exams(year=None, department=None):
    """Retrieves exam schedule, optionally filtered by year and department."""
    conn = get_db_connection()
    c = conn.cursor()
    if year and department:
        c.execute('SELECT * FROM exams WHERE year=? AND department=? ORDER BY exam_date ASC', (year, department))
    else:
        c.execute('SELECT * FROM exams ORDER BY exam_date ASC')
    data = c.fetchall()
    conn.close()
    return data

def delete_exam(exam_id):
    """Deletes an exam entry and its physical file."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT file_path FROM exams WHERE id = ?', (exam_id,))
    res = c.fetchone()
    if res and res[0]:
        abs_path = os.path.join('static', res[0])
        if os.path.exists(abs_path):
            try: os.remove(abs_path)
            except: pass
            
    c.execute('DELETE FROM exams WHERE id = ?', (exam_id,))
    c.execute('DELETE FROM global_exams WHERE id = ?', (exam_id,))
    conn.commit()
    conn.close()

def delete_assignment(assignment_id):
    """Deletes an assignment and its physical file."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT file_path FROM assignments WHERE id = ?', (assignment_id,))
    res = c.fetchone()
    if res and res[0]:
        abs_path = os.path.join('static', res[0])
        if os.path.exists(abs_path):
            try: os.remove(abs_path)
            except: pass
            
    c.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
    c.execute('DELETE FROM student_activity WHERE assignment_id = ?', (assignment_id,))
    conn.commit()
    conn.close()

# --- ADMIN HUB FUNCTIONS ---

def add_activity_log(user_id, action, details="", ip_address=""):
    """Records a system activity log."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
              (user_id, action, details, ip_address))
    conn.commit()
    conn.close()

def get_admin_dashboard_stats():
    """Fetches high-level stats and growth metrics for the admin dashboard."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 7-day growth
    c.execute("SELECT COUNT(*) FROM users WHERE is_approved = 1 AND id IN (SELECT id FROM users LIMIT 1000) -- Mocking registration date since it's missing in schema") 
    # Actually I should add created_at to users. For now let's just return realistic counts.
    
    stats = {
        'total_users': c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'pending_approvals': c.execute("SELECT COUNT(*) FROM users WHERE is_approved = 0").fetchone()[0],
        'active_today': c.execute("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE DATE(created_at) = DATE('now')").fetchone()[0],
        'total_assignments': c.execute("SELECT COUNT(*) FROM student_answers").fetchone()[0], # Mocking content count
        'upcoming_exams': c.execute("SELECT COUNT(*) FROM exams WHERE exam_date >= DATE('now')").fetchone()[0]
    }
    conn.close()
    return stats

def get_all_activity_logs(limit=100):
    """Fetches system logs."""
    import pandas as pd
    conn = get_db_connection()
    query = """
        SELECT al.*, u.username, u.role
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    return df

def update_system_setting(key, value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_system_settings():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM system_settings")
    settings = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return settings

def add_announcement(title, message, target_role="All"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO announcements (title, message, target_role) VALUES (?, ?, ?)", (title, message, target_role))
    conn.commit()
    conn.close()

def update_user_status(user_id, status, is_blocked=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status = ?, is_blocked = ? WHERE id = ?", (status, is_blocked, user_id))
    conn.commit()
    conn.close()

def update_last_login(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_exam(exam_id, subject, exam_date):
    """Updates an exam entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE exams SET subject = ?, exam_date = ? WHERE id = ?', (subject, exam_date, exam_id))
    conn.commit()
    conn.close()

def add_todo(user_id, task):
    """Adds a new to-do task."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO todos (user_id, task) VALUES (?, ?)', (user_id, task))
    conn.commit()
    conn.close()

def get_todos(user_id):
    """Retrieves all tasks for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, task, is_completed FROM todos WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def toggle_todo(todo_id, current_status):
    """Toggles task status. Returns True if became completed (for points logic)."""
    conn = get_db_connection()
    c = conn.cursor()
    new_status = not current_status
    c.execute('UPDATE todos SET is_completed = ? WHERE id = ?', (new_status, todo_id))
    conn.commit()
    conn.close()
    return new_status

def delete_todo(todo_id):
    """Deletes a task."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()

# --- Notifications ---
def add_notification(user_id, message):
    """Adds a notification for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)', (user_id, message))
    conn.commit()
    conn.close()

def get_notifications(user_id, unread_only=False):
    """Retrieves notifications for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    if unread_only:
        c.execute('SELECT id, message, is_read, created_at FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC', (user_id,))
    else:
        c.execute('SELECT id, message, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def mark_notifications_read(user_id):
    """Marks all notifications for a user as read."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# --- Discussions ---
def add_discussion(topic_id, user_id, comment, parent_id=None):
    """Adds a comment to a topic discussion."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO discussions (topic_id, user_id, comment, parent_id) VALUES (?, ?, ?, ?)', (topic_id, user_id, comment, parent_id))
    conn.commit()
    conn.close()

def get_discussions(topic_id):
    """Retrieves all discussions for a topic, with user names."""
    conn = get_db_connection()
    c = conn.cursor()
    query = """
        SELECT d.id, d.comment, d.created_at, u.username, u.role, d.parent_id
        FROM discussions d
        JOIN users u ON d.user_id = u.id
        WHERE d.topic_id = ?
        ORDER BY d.created_at ASC
    """
    c.execute(query, (topic_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- Admin Helpers ---
def update_user_role(user_id, new_role):
    """Updates the role of a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Deletes a user by ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Library Helpers ---
def add_resource(subject_id, title, author, edition, file_path, file_size, res_type, uploader_id, resource_url=None, year=None, department=None):
    """Adds a new resource to the hub."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO resources (subject_id, title, author, edition, file_path, file_size, type, uploader_id, resource_url, year, department) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (subject_id, title, author, edition, file_path, file_size, res_type, uploader_id, resource_url, year, department))
    conn.commit()
    conn.close()

def delete_resource(resource_id):
    """Deletes a resource and its physical file."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT file_path FROM resources WHERE id = ?", (resource_id,))
    res = c.fetchone()
    if res and res[0]:
        # Support both old and new path formats
        path = res[0]
        if not path.startswith('static'):
            abs_path = os.path.join('static', path) if not os.path.exists(path) else path
        else:
            abs_path = path
            
        if os.path.exists(abs_path):
            try: os.remove(abs_path)
            except: pass
            
        c.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        c.execute("DELETE FROM download_history WHERE resource_id = ?", (resource_id,))
        c.execute("DELETE FROM favorites WHERE resource_id = ?", (resource_id,))
        conn.commit()
    conn.close()

def update_resource(resource_id, title, author, edition, type, subject_id, year=None, department=None):
    """Updates resource metadata including targeting."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''UPDATE resources SET title = ?, author = ?, edition = ?, type = ?, subject_id = ?, year = ?, department = ? 
                 WHERE id = ?''', 
              (title, author, edition, type, subject_id, year, department, resource_id))
    conn.commit()
    conn.close()

def get_resources(subject_id=None, search_query=None, year=None, department=None):
    """Retrieves resources with optional filtering."""
    conn = get_db_connection()
    query = "SELECT r.*, s.name as subject_name FROM resources r LEFT JOIN subjects s ON r.subject_id = s.id WHERE 1=1"
    params = []
    if subject_id:
        query += " AND r.subject_id = ?"
        params.append(subject_id)
    if search_query:
        query += " AND (r.title LIKE ? OR r.author LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if year:
        query += " AND r.year = ?"
        params.append(year)
    if department:
        query += " AND r.department = ?"
        params.append(department)
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def track_download(user_id, resource_id):
    """Logs a download event."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO download_history (user_id, resource_id) VALUES (?, ?)", (user_id, resource_id))
    conn.commit()
    conn.close()

def get_download_history(user_id, limit=5):
    """Retrieves recent downloads for a user."""
    conn = get_db_connection()
    query = """
        SELECT r.title, r.type, h.downloaded_at, r.file_path
        FROM download_history h
        JOIN resources r ON h.resource_id = r.id
        WHERE h.user_id = ?
        ORDER BY h.downloaded_at DESC
        LIMIT ?
    """
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=(user_id, limit))
    conn.close()
    return df

def toggle_favorite(user_id, resource_id):
    """Toggles a resource as a favorite."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM favorites WHERE user_id = ? AND resource_id = ?", (user_id, resource_id))
    if c.fetchone():
        c.execute("DELETE FROM favorites WHERE user_id = ? AND resource_id = ?", (user_id, resource_id))
        conn.commit()
        conn.close()
        return False
    else:
        c.execute("INSERT INTO favorites (user_id, resource_id) VALUES (?, ?)", (user_id, resource_id))
        conn.commit()
        conn.close()
        return True

def get_favorites(user_id):
    """Gets favorite resource IDs for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT resource_id FROM favorites WHERE user_id = ?", (user_id,))
    favs = [r[0] for r in c.fetchall()]
    conn.close()
    return favs

def get_leaderboard(limit=10):
    """Retrieves top users by XP."""
    conn = get_db_connection()
    c = conn.cursor()
    # Prioritize XP, then legacy points
    c.execute("SELECT username, xp FROM users WHERE role = 'Student' ORDER BY xp DESC, points DESC LIMIT ?", (limit,))
    data = c.fetchall()
    conn.close()
    return data

def get_topic_note(user_id, topic_id):
    """Retrieves the note for a specific topic and user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT content FROM topic_notes WHERE user_id = ? AND topic_id = ?", (user_id, topic_id))
    result = c.fetchone()
    conn.close()
    return result[0] if result else ""

def save_topic_note(user_id, topic_id, content):
    """Saves or updates a topic note."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO topic_notes (user_id, topic_id, content, updated_at) 
                 VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                 ON CONFLICT(user_id, topic_id) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at''',
              (user_id, topic_id, content))
    conn.commit()
    conn.close()

def get_student_progress(user_id):
    """Retrieves student progress stats and recent scores."""
    import pandas as pd
    conn = get_db_connection()
    # Get topics completed vs total topics
    total_topics = pd.read_sql_query("SELECT COUNT(*) as count FROM topics", conn).iloc[0]['count']
    completed_topics = pd.read_sql_query("SELECT COUNT(*) as count FROM student_progress WHERE user_id = ? AND completed = 1", conn, params=(user_id,)).iloc[0]['count']
    
    # Get recent scores
    scores_df = pd.read_sql_query("""
        SELECT q.question_text, sa.answer, sa.is_correct, sa.score, sa.submitted_at 
        FROM student_answers sa 
        JOIN questions q ON sa.question_id = q.id 
        WHERE sa.user_id = ? 
        ORDER BY sa.submitted_at DESC LIMIT 5
    """, conn, params=(user_id,))
    conn.close()
    return total_topics, completed_topics, scores_df

# --- Assigned Tasks (Staff to Student) ---

def add_assigned_task(staff_id, title, description, due_date, task_url=None, file_path=None, year=None, department=None):
    """Adds a new task assigned by staff."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO assigned_tasks (staff_id, title, description, due_date, task_url, file_path, year, department) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
              (staff_id, title, description, due_date, task_url, file_path, year, department))
    conn.commit()
    conn.close()

def get_assigned_tasks_for_staff():
    """Retrieves all tasks assigned by staff with detailed completion and engagement stats."""
    conn = get_db_connection()
    # SQL to get counts and grouped names for Finished, Opened (but not finished), and Not Started
    query = """
        SELECT t.*, u.username as staff_name,
               (SELECT COUNT(*) FROM student_task_completions WHERE task_id = t.id AND is_completed = 1) as completed_count,
               (SELECT COUNT(*) FROM users WHERE role = 'Student') as total_students,
               
               -- Names of students who FINISHED
               (SELECT GROUP_CONCAT(u2.username) 
                FROM users u2 JOIN student_task_completions c ON u2.id = c.student_id 
                WHERE c.task_id = t.id AND c.is_completed = 1) as finished_names,
               -- Names of students who OPENED (viewed) but NOT FINISHED
               (SELECT GROUP_CONCAT(u3.username) 
                FROM users u3 JOIN student_task_completions c ON u3.id = c.student_id 
                WHERE c.task_id = t.id AND c.viewed_at IS NOT NULL AND (c.is_completed = 0 OR c.is_completed IS NULL)) as opened_names,
                
               -- Names of students who have NOT STARTED (no record in completions table)
               (SELECT GROUP_CONCAT(u4.username) 
                FROM users u4 
                WHERE u4.role = 'Student' 
                AND u4.id NOT IN (SELECT student_id FROM student_task_completions WHERE task_id = t.id)) as pending_names
        FROM assigned_tasks t
        JOIN users u ON t.staff_id = u.id
        ORDER BY t.created_at DESC
    """
    import pandas as pd
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def mark_task_viewed(task_id, student_id):
    """Marks a task as opened by a student if it hasn't been already."""
    conn = get_db_connection()
    c = conn.cursor()
    # Insert ignore/handle duplicate
    c.execute("SELECT id FROM student_task_completions WHERE task_id = ? AND student_id = ?", (task_id, student_id))
    row = c.fetchone()
    if row:
        # Update only if viewed_at is null
        c.execute("UPDATE student_task_completions SET viewed_at = COALESCE(viewed_at, CURRENT_TIMESTAMP) WHERE id = ?", (row[0],))
    else:
        c.execute("INSERT INTO student_task_completions (task_id, student_id, viewed_at, is_completed) VALUES (?, ?, CURRENT_TIMESTAMP, 0)", 
                  (task_id, student_id))
    conn.commit()
    conn.close()

def get_assigned_tasks_for_student(student_id, year=None, department=None):
    """Retrieves tasks for a student with their completion status, filtered by year and department."""
    conn = get_db_connection()
    # Left join to get all staff tasks and then the completion status for THIS student
    query = """
        SELECT t.id, t.title, t.description, t.due_date, t.task_url, t.file_path, u.username as staff_name,
               COALESCE(c.is_completed, 0) as is_completed, t.year, t.department
        FROM assigned_tasks t
        JOIN users u ON t.staff_id = u.id
        LEFT JOIN student_task_completions c ON t.id = c.task_id AND c.student_id = ?
        WHERE 1=1
    """
    params = [student_id]
    
    if year:
        query += " AND t.year = ?"
        params.append(year)
    if department:
        query += " AND t.department = ?"
        params.append(department)
        
    query += " ORDER BY t.due_date ASC, t.created_at DESC"
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_pending_task_count(student_id):
    """Returns the number of staff tasks not yet completed by the student."""
    conn = get_db_connection()
    c = conn.cursor()
    # Count all tasks minus those completed by this student
    query = """
        SELECT COUNT(*) FROM assigned_tasks t
        WHERE t.id NOT IN (
            SELECT task_id FROM student_task_completions 
            WHERE student_id = ? AND is_completed = 1
        )
    """
    c.execute(query, (student_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def toggle_assigned_task_completion(task_id, student_id):
    """Toggles completion status for an assigned task. Returns True if became completed."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check current status
    c.execute("SELECT is_completed FROM student_task_completions WHERE task_id = ? AND student_id = ?", (task_id, student_id))
    result = c.fetchone()
    
    if result:
        new_status = not bool(result[0])
        c.execute("UPDATE student_task_completions SET is_completed = ?, completed_at = CURRENT_TIMESTAMP WHERE task_id = ? AND student_id = ?",
                  (new_status, task_id, student_id))
    else:
        new_status = True
        c.execute("INSERT INTO student_task_completions (task_id, student_id, is_completed, completed_at) VALUES (?, ?, 1, CURRENT_TIMESTAMP)",
                  (task_id, student_id))
    
    conn.commit()
    conn.close()
    return new_status

def mark_assigned_task_complete(task_id, student_id):
    """Marks an assigned task as complete. Idempotent. Returns True if newly completed."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_completed FROM student_task_completions WHERE task_id = ? AND student_id = ?", (task_id, student_id))
    result = c.fetchone()
    newly_completed = False
    if not result:
        c.execute("INSERT INTO student_task_completions (task_id, student_id, is_completed, completed_at) VALUES (?, ?, 1, CURRENT_TIMESTAMP)",
                  (task_id, student_id))
        conn.commit()
        newly_completed = True
    elif not result[0]:
        c.execute("UPDATE student_task_completions SET is_completed = 1, completed_at = CURRENT_TIMESTAMP WHERE task_id = ? AND student_id = ?",
                  (task_id, student_id))
        conn.commit()
        newly_completed = True
    conn.close()
    return newly_completed

def delete_assigned_task(task_id):
    """Deletes an assigned task and its completions."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM assigned_tasks WHERE id = ?", (task_id,))
    c.execute("DELETE FROM student_task_completions WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()

def get_task_completions(task_id):
    """Retrieves completion status for all students for a specific task."""
    conn = get_db_connection()
    query = """
        SELECT u.username, 
               COALESCE(c.is_completed, 0) as is_completed,
               c.completed_at
        FROM users u
        LEFT JOIN student_task_completions c ON u.id = c.student_id AND c.task_id = ?
        WHERE u.role = 'Student'
        ORDER BY u.username ASC
    """
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=(task_id,))
    conn.close()
    return df

# --- Global Exams (Staff Managed) ---

def add_global_exam(subject, exam_date, year=None, department=None):
    """Adds a new global exam entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO global_exams (subject, exam_date, year, department) VALUES (?, ?, ?, ?)', 
              (subject, exam_date, year, department))
    conn.commit()
    conn.close()

def get_global_exams(year=None, department=None):
    """Retrieves global exams, optionally filtered by year and department."""
    conn = get_db_connection()
    c = conn.cursor()
    query = 'SELECT id, subject, exam_date, year, department FROM global_exams WHERE 1=1'
    params = []
    
    if year:
        query += " AND year = ?"
        params.append(year)
    if department:
        query += " AND department = ?"
        params.append(department)
        
    query += " ORDER BY exam_date ASC"
    
    c.execute(query, params)
    data = c.fetchall()
    conn.close()
    return data

def delete_global_exam(exam_id):
    """Deletes a global exam entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM global_exams WHERE id = ?', (exam_id,))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

def get_all_students_engagement_list(year=None, department=None):
    """Retrieves a summary of all students and their task engagement."""
    conn = get_db_connection()
    query = """
        SELECT u.id, u.username, u.email, u.points, u.year, u.department,
               (SELECT COUNT(*) FROM assigned_tasks t WHERE t.year = u.year AND t.department = u.department) as total_tasks,
               (SELECT COUNT(*) FROM student_task_completions WHERE student_id = u.id AND is_completed = 1) as tasks_finished,
               (SELECT COUNT(*) FROM student_task_completions WHERE student_id = u.id AND viewed_at IS NOT NULL AND (is_completed = 0 OR is_completed IS NULL)) as tasks_opened
        FROM users u
        WHERE u.role = 'Student'
    """
    params = []
    if year:
        query += " AND u.year = ?"
        params.append(year)
    if department:
        query += " AND u.department = ?"
        params.append(department)
        
    query += " ORDER BY u.points DESC, u.username ASC"
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_student_task_details(student_id):
    """Retrieves the status of every assigned task for a specific student."""
    conn = get_db_connection()
    query = """
        SELECT t.id, t.title, t.due_date,
               CASE 
                   WHEN c.is_completed = 1 THEN 'Finished ✅'
                   WHEN c.viewed_at IS NOT NULL THEN 'Opened 👁️'
                   ELSE 'Not Started ⏳'
               END as status,
               c.completed_at,
               c.viewed_at
        FROM assigned_tasks t
        LEFT JOIN student_task_completions c ON t.id = c.task_id AND c.student_id = ?
        ORDER BY t.due_date ASC
    """
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=(student_id,))
    conn.close()
    return df

# --- Staff Portal Features (Marks, Attendance, Feedback) ---

def add_internal_mark(student_id, subject_id, test_name, marks, total):
    """Adds a record for internal marks."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO internal_marks (student_id, subject_id, test_name, marks_obtained, total_marks)
                 VALUES (?, ?, ?, ?, ?)''', (student_id, subject_id, test_name, marks, total))
    conn.commit()
    conn.close()

def get_internal_marks(student_id=None, subject_id=None):
    """Retrieves internal marks with optional filters."""
    conn = get_db_connection()
    query = """
        SELECT m.*, u.username as student_name, s.name as subject_name
        FROM internal_marks m
        JOIN users u ON m.student_id = u.id
        JOIN subjects s ON m.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if student_id:
        query += " AND m.student_id = ?"
        params.append(student_id)
    if subject_id:
        query += " AND m.subject_id = ?"
        params.append(subject_id)
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def record_attendance(student_id, subject_id, date, status):
    """Records student attendance."""
    conn = get_db_connection()
    c = conn.cursor()
    # Check if entry exists for this student/subject/date
    c.execute("SELECT id FROM attendance WHERE student_id = ? AND subject_id = ? AND date = ?", (student_id, subject_id, date))
    row = c.fetchone()
    if row:
        c.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, row[0]))
    else:
        c.execute("INSERT INTO attendance (student_id, subject_id, date, status) VALUES (?, ?, ?, ?)", (student_id, subject_id, date, status))
    conn.commit()
    conn.close()

def get_attendance_report(student_id=None, subject_id=None):
    """Retrieves attendance records."""
    conn = get_db_connection()
    query = """
        SELECT a.*, u.username as student_name, s.name as subject_name
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if student_id:
        query += " AND a.student_id = ?"
        params.append(student_id)
    if subject_id:
        query += " AND a.subject_id = ?"
        params.append(subject_id)
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_attendance_summary(student_id):
    """Calculates attendance percentage per subject for a student."""
    conn = get_db_connection()
    query = """
        SELECT s.name as subject_name,
               COUNT(*) as total_classes,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = ?
        GROUP BY s.name
    """
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=(student_id,))
    conn.close()
    
    if not df.empty:
        df['attendance_percentage'] = (df['present_count'] / df['total_classes'] * 100).round(1)
    
    return df

def add_feedback(student_id, subject_id, rating, comment):
    """Adds student feedback for a course/subject."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO feedback (student_id, subject_id, rating, comment) VALUES (?, ?, ?, ?)", (student_id, subject_id, rating, comment))
    conn.commit()
    conn.close()

def get_feedback_list(subject_id=None):
    """Retrieves feedback list."""
    conn = get_db_connection()
    query = """
        SELECT f.*, u.username as student_name, s.name as subject_name
        FROM feedback f
        JOIN users u ON f.student_id = u.id
        JOIN subjects s ON f.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += " AND f.subject_id = ?"
        params.append(subject_id)
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
def add_question_pdf(topic, q_type, file_path, year=None, department=None):
    """Adds a new PDF question bank entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO question_bank (topic, type, file_path, year, department) VALUES (?, ?, ?, ?, ?)', 
              (topic, q_type, file_path, year, department))
    conn.commit()
    conn.close()

def get_question_pdfs(year=None, department=None):
    """Retrieves question bank PDFs, optionally filtered by year and department."""
    conn = get_db_connection()
    import pandas as pd
    query = "SELECT * FROM question_bank WHERE 1=1"
    params = []
    
    if year:
        query += " AND year = ?"
        params.append(year)
    if department:
        query += " AND department = ?"
        params.append(department)
        
    query += " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def delete_question_pdf(pdf_id):
    """Deletes a question bank PDF and its file."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT file_path FROM question_bank WHERE id = ?", (pdf_id,))
    res = c.fetchone()
    if res:
        file_path = res[0]
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        c.execute("DELETE FROM question_bank WHERE id = ?", (pdf_id,))
        conn.commit()
    conn.close()
# --- New Assignment & XP System Helpers ---

def add_assignment(staff_id, title, description, year, department, file_path=None, task_url=None):
    """Adds a new assignment."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO assignments (staff_id, title, description, year, department, file_path, task_url) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (staff_id, title, description, year, department, file_path, task_url))
    conn.commit()
    conn.close()

def get_filtered_assignments(year=None, department=None, student_id=None):
    """Retrieves assignments filtered by year and department, with completion status for a student."""
    conn = get_db_connection()
    import pandas as pd
    
    query = """
        SELECT a.*, u.username as staff_name, 
               COALESCE(sa.status, 'pending') as status,
               COALESCE(sa.xp, 0) as earned_xp
        FROM assignments a
        JOIN users u ON a.staff_id = u.id
        LEFT JOIN student_activity sa ON a.id = sa.assignment_id AND sa.student_id = ?
        WHERE 1=1
    """
    params = [student_id]
    
    if year:
        query += " AND a.year = ?"
        params.append(year)
    if department:
        query += " AND a.department = ?"
        params.append(department)
        
    query += " ORDER BY a.created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def track_assignment_view(student_id, assignment_id):
    """Records that a student viewed an assignment and awards 5 XP."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # STEP 4: Avoid Duplicate Entry
        c.execute("SELECT id FROM student_activity WHERE student_id=? AND assignment_id=?", (student_id, assignment_id))
        if not c.fetchone():
            # Insert only if not exists
            c.execute("""
            INSERT INTO student_activity (student_id, assignment_id, status, xp)
            VALUES (?, ?, 'viewed', 5)
            """, (student_id, assignment_id))
            
            # Award XP for first view
            c.execute("UPDATE users SET xp = xp + 5 WHERE id=?", (student_id,))
            conn.commit()
    except Exception as e:
        print(f"Error tracking view: {e}")
    finally:
        conn.close()

def complete_assignment(student_id, assignment_id):
    """Marks an assignment as completed and awards 20 XP."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # STEP 5 & 6: Student Completes & Update XP
        c.execute("SELECT status FROM student_activity WHERE student_id=? AND assignment_id=?", (student_id, assignment_id))
        res = c.fetchone()
        
        if res and res[0] != 'completed':
            c.execute("""
            UPDATE student_activity
            SET status='completed', xp=20, submitted_at=CURRENT_TIMESTAMP
            WHERE student_id=? AND assignment_id=?
            """, (student_id, assignment_id))
            
            # Update Student XP (+15 more to make it 20 total, or +20 as per user snippet)
            # User snippet says "SET xp = xp + 20", so I'll follow that.
            c.execute("UPDATE users SET xp = xp + 20 WHERE id=?", (student_id,))
            conn.commit()
        elif not res:
            # Direct completion without view
            c.execute("""
            INSERT INTO student_activity (student_id, assignment_id, status, xp, submitted_at)
            VALUES (?, ?, 'completed', 20, CURRENT_TIMESTAMP)
            """, (student_id, assignment_id))
            c.execute("UPDATE users SET xp = xp + 20 WHERE id=?", (student_id,))
            conn.commit()
            
    except Exception as e:
        print(f"Error completing assignment: {e}")
    finally:
        conn.close()

def get_assignment_activity_report():
    """Retrieves full student activity report for staff (STEP 7)."""
    conn = get_db_connection()
    import pandas as pd
    query = """
        SELECT s.username as student_name, a.title as assignment_title, sa.status, sa.submitted_at, sa.xp
        FROM student_activity sa
        JOIN users s ON sa.student_id = s.id
        JOIN assignments a ON sa.assignment_id = a.id
        ORDER BY sa.submitted_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- ADMIN HUB FUNCTIONS ---

def add_activity_log(user_id, action, details="", ip_address=""):
    """Records a system activity log."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
              (user_id, action, details, ip_address))
    conn.commit()
    conn.close()

def get_admin_dashboard_stats():
    """Fetches high-level stats and growth metrics for the admin dashboard."""
    conn = get_db_connection()
    c = conn.cursor()
    
    stats = {
        'total_users': c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'pending_approvals': c.execute("SELECT COUNT(*) FROM users WHERE is_approved = 0").fetchone()[0],
        'active_today': c.execute("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE DATE(created_at) = DATE('now')").fetchone()[0],
        'total_assignments': c.execute("SELECT COUNT(*) FROM assignments").fetchone()[0],
        'upcoming_exams': c.execute("SELECT COUNT(*) FROM exams WHERE exam_date >= DATE('now')").fetchone()[0],
        'staff': c.execute("SELECT COUNT(*) FROM users WHERE role = 'Staff'").fetchone()[0],
        'admins': c.execute("SELECT COUNT(*) FROM users WHERE role = 'Admin'").fetchone()[0]
    }
    conn.close()
    return stats

def get_all_activity_logs(limit=100):
    """Fetches system logs."""
    import pandas as pd
    conn = get_db_connection()
    query = """
        SELECT al.*, u.username, u.role
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    return df

def update_system_setting(key, value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_system_settings():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM system_settings")
    settings = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return settings

def add_announcement(title, message, target_role="All"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO announcements (title, message, target_role) VALUES (?, ?, ?)", (title, message, target_role))
    conn.commit()
    conn.close()

def update_user_status(user_id, status, is_blocked=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status = ?, is_blocked = ? WHERE id = ?", (status, is_blocked, user_id))
    conn.commit()
    conn.close()

def update_last_login(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
