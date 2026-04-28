import os
from jinja2 import Environment, FileSystemLoader

template_dir = os.path.join(os.getcwd(), 'templates')
env = Environment(loader=FileSystemLoader(template_dir))

def check_template(name):
    try:
        env.get_template(name)
        print(f"[OK] {name} passed syntax check.")
    except Exception as e:
        print(f"[ERROR] {name} failed: {e}")

check_template('layout.html')
check_template('gpa_calculator.html')
check_template('library.html')
check_template('placement.html')
