import sqlite3
conn = sqlite3.connect('student.db')
c = conn.cursor()

# Fix academic_years to match user_profile.html values
c.execute("UPDATE academic_years SET name='First Year' WHERE name='1st Year'")
c.execute("UPDATE academic_years SET name='Second Year' WHERE name='2nd Year'")
c.execute("UPDATE academic_years SET name='Third Year' WHERE name='3rd Year'")
# Final Year already matches
conn.commit()

print("Updated! New values:")
c.execute("SELECT * FROM academic_years")
for r in c.fetchall():
    print(f"  {r}")

conn.close()
