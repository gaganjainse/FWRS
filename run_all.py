#!/usr/bin/env python3
import os, subprocess, sys, shlex

ROOT = os.path.abspath(os.path.dirname(__file__))
VENV_DIR = os.path.join(ROOT, '.venv')
PYTHON_IN_VENV = os.path.join(VENV_DIR, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(VENV_DIR, 'bin', 'python')

def ensure_venv():
    if not os.path.exists(VENV_DIR):
        print('Creating virtual environment...')
        subprocess.check_call([sys.executable, '-m', 'venv', VENV_DIR])
    # prefer venv python for pip installs and running apps
    return PYTHON_IN_VENV if os.path.exists(PYTHON_IN_VENV) else sys.executable

def install_requirements(python_exec):
    print('Installing requirements using', python_exec)
    try:
        subprocess.check_call([python_exec, '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.check_call([python_exec, '-m', 'pip', 'install', '-r', os.path.join(ROOT, 'requirements.txt')])
        print('Requirements installed.')
    except subprocess.CalledProcessError as e:
        print('pip install failed:', e)

def run_desktop(python_exec):
    print('Starting Desktop GUI...')
    subprocess.check_call([python_exec, os.path.join('ui', 'desktop_app.py')], cwd=ROOT)

def run_web(python_exec):
    print('Starting Web App (Flask) on http://127.0.0.1:5000 ...')
    # Use flask cli if available through venv python -m flask --app ui.web.app run
    subprocess.check_call([python_exec, '-m', 'flask', '--app', 'ui.web.app', 'run'], cwd=ROOT)

def generate_map(python_exec):
    print('Generating folium map (map.html) ...')
    subprocess.check_call([python_exec, os.path.join('ui', 'map_generator.py')], cwd=ROOT)
    mapfile = os.path.join(ROOT, 'map.html')
    if os.path.exists(mapfile):
        if sys.platform.startswith('win'):
            os.startfile(mapfile)
        else:
            try:
                subprocess.check_call(['xdg-open', mapfile])
            except Exception:
                print('Open map at:', mapfile)

def run_lp_export(python_exec):
    print('Running LP and exporting CSVs...')
    subprocess.check_call([python_exec, 'main.py', '--export', 'allocs.csv', '--export-summary', 'summary.csv'], cwd=ROOT)
    print('Done. Files: allocs.csv, summary.csv')

def main():
    python_exec = ensure_venv()
    while True:
        print('=================================')
        print(' Food Wastage LP System Launcher ')
        print('=================================')
        print('1) Run Desktop GUI (Tkinter)')
        print('2) Run Web App (Flask)')
        print('3) Generate Folium Map (map.html)')
        print('4) Run LP and export CSVs')
        print('5) Install/Update requirements')
        print('6) Exit')
        choice = input('Enter choice (1-6): ').strip()
        if choice == '1':
            run_desktop(python_exec)
        elif choice == '2':
            run_web(python_exec)
        elif choice == '3':
            generate_map(python_exec)
        elif choice == '4':
            run_lp_export(python_exec)
        elif choice == '5':
            install_requirements(python_exec)
        elif choice == '6':
            print('Goodbye.')
            break
        else:
            print('Invalid choice. Please enter 1-6.')

if __name__ == '__main__':
    main()
