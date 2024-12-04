import os
import django
from django.core.management import call_command

# ตั้งค่า DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ran_domaroi.settings')

# เริ่มต้น Django
django.setup()

# เรียกใช้คำสั่ง dumpdata
with open('initial_data.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', 'core.Category', 'core.SubCategory', indent=4, stdout=f)
