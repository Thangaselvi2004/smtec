import os

filepath = 'templates/staff_portal.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Start Dashboard Tab
content = content.replace('<div class="main-content">', '<div class="main-content">\n        <!-- Dashboard Tab -->\n        <div id="tab-dashboard" class="tab-pane active">')

# 2. End Dashboard, Start Students, Start Courses
dashboard_end = '''
        </div> <!-- End Dashboard Tab -->

        <!-- Students Tab -->
        <div id="tab-students" class="tab-pane">
            <div class="welcome-header">
                <h1>Student Management</h1>
                <p>View all students, predict performance, and identify at-risk students.</p>
            </div>
            <div class="action-grid">
                <a href="{{ url_for('student_monitoring') }}" class="action-card" style="grid-column: 1 / -1; justify-content: center; text-align: center;">
                    <div class="action-info" style="flex: none;">
                        <h3><i class="fas fa-external-link-alt"></i> Open Full Student Database & ML Predictions</h3>
                        <p>Click here to access the comprehensive student monitoring tool with AI insights.</p>
                    </div>
                </a>
            </div>
        </div>

        <!-- Courses Tab -->
        <div id="tab-courses" class="tab-pane">
            <div class="welcome-header">
                <h1>Course & Content Management</h1>
                <p>Add subjects, units, question banks, and exams.</p>
            </div>
            <div class="action-grid" style="margin-bottom: 40px;">
                <a href="{{ url_for('syllabus') }}" class="action-card" style="grid-column: 1 / -1;">
                    <div class="action-icon"><i class="fas fa-book-open"></i></div>
                    <div class="action-info">
                        <h3>Syllabus & Curriculum</h3>
                        <p>View the complete course structure and detailed syllabus for all departments.</p>
                    </div>
                </a>
            </div>
'''
content = content.replace('        <!-- Management Sections -->', dashboard_end)

# 3. End Courses, Start Assignments
courses_end = '''
        </div> <!-- End Courses Tab -->

        <!-- Assignments Tab -->
        <div id="tab-assignments" class="tab-pane">
            <div class="welcome-header">
                <h1>Task & Assignment Management</h1>
                <p>Create and allocate tasks for all students.</p>
            </div>
'''
content = content.replace('        <div id="tasks" class="quick-links"', courses_end + '\n        <div id="tasks" class="quick-links"')

# 4. End Assignments, Start Evaluation
assignments_end = '''
        </div> <!-- End Assignments Tab -->

        <!-- Evaluation Tab -->
        <div id="tab-evaluation" class="tab-pane">
            <div class="welcome-header">
                <h1>Manual Evaluation System</h1>
                <p>Grade submissions, enter internal marks, and track attendance.</p>
            </div>
            <div class="action-grid" style="margin-bottom: 40px;">
                <a href="{{ url_for('staff_marks') }}" class="action-card">
                    <div class="action-icon"><i class="fas fa-plus-circle"></i></div>
                    <div class="action-info">
                        <h3>Internal Marks</h3>
                        <p>Input and manage internal assessment marks.</p>
                    </div>
                </a>
                <a href="{{ url_for('staff_attendance') }}" class="action-card">
                    <div class="action-icon"><i class="fas fa-user-check"></i></div>
                    <div class="action-info">
                        <h3>Attendance Entry</h3>
                        <p>Record daily student attendance.</p>
                    </div>
                </a>
            </div>
'''
content = content.replace('        <div id="grading" class="quick-links"', assignments_end + '\n        <div id="grading" class="quick-links"')

# 5. Move Exams into Courses tab:
# Wait, let's just make Exams its own tab or put it in Courses.
# Let's put Exams at the end, before the final </div> of main-content.
eval_end = '''
        </div> <!-- End Evaluation Tab -->

        <!-- Analytics Tab -->
        <div id="tab-analytics" class="tab-pane">
            <div class="welcome-header">
                <h1>Performance Analytics (ML)</h1>
                <p>Identify weak students and suggest improvements using AI.</p>
            </div>
            <div class="glass-card" style="text-align: center; padding: 50px;">
                <i class="fas fa-chart-bar" style="font-size: 3rem; color: var(--primary); margin-bottom: 20px;"></i>
                <h3>Analytics Dashboard</h3>
                <p>Global student performance graphs.</p>
                <a href="{{ url_for('student_monitoring') }}" class="btn-aurora" style="display: inline-block; margin-top: 20px;">View Detailed Predictions</a>
            </div>
        </div>

        <!-- Resources Tab -->
        <div id="tab-resources" class="tab-pane">
            <div class="welcome-header">
                <h1>Global Resource Management</h1>
                <p>Upload PDFs, interview guides, and lecture notes.</p>
            </div>
            <div class="action-grid">
                <a href="{{ url_for('library') }}" class="action-card" style="grid-column: 1 / -1;">
                    <div class="action-icon"><i class="fas fa-book-reader"></i></div>
                    <div class="action-info">
                        <h3>Study Materials</h3>
                        <p>Upload lecture notes, textbooks, and previous year question papers.</p>
                    </div>
                </a>
            </div>
        </div>

        <!-- Leaderboard Tab -->
        <div id="tab-leaderboard" class="tab-pane">
            <div class="welcome-header">
                <h1>Gamification & Leaderboard</h1>
                <p>Monitor student XP and top performers.</p>
            </div>
            <div class="glass-card" style="text-align: center; padding: 50px;">
                <i class="fas fa-trophy" style="font-size: 3rem; color: #ffb74d; margin-bottom: 20px;"></i>
                <h3>Global Leaderboard Overview</h3>
                <p>Student rankings based on XP earned.</p>
                <a href="{{ url_for('student_monitoring') }}" class="btn-aurora" style="display: inline-block; margin-top: 20px;">View Student XP</a>
            </div>
        </div>
'''
content = content.replace('        <div id="exams" class="quick-links"', eval_end + '\n        <div id="exams" class="quick-links"')

# Make sure Exams div is closed correctly.
# The exams div closes at the very end of main-content. Let's just wrap it in an Exams tab? No, let's put it in the Courses tab by moving it, OR we can just wrap it in a new tab if we want. But the user didn't ask for an Exams tab. They said "Courses" has subjects, units, question banks. We will append the Exams div to Courses later, or just leave it visible inside the Analytics tab? No, Exams is a quick-links div. Let's change `<div id="exams"` to be inside Courses, or simply we can leave it as the last element of Evaluation. Let's wrap it in an empty tab, or we can just append a `</div> <!-- End Leaderboard -->` after it if we wrapped Exams into Leaderboard.

# To be clean, I will just do a direct string replace of the entire `staff_portal.html`.
