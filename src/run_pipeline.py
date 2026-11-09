import subprocess
import sys

SCRIPTS = [
    'src/prepare.py',
    'src/build_mart.py',
    'src/scoring.py',
]

for script in SCRIPTS:
    print(f'Начался запуск {script}...')
    subprocess.run([sys.executable, script], check=True)

print('Пайплайн завершён: витрина и рейтинг пересобраны успешно.')