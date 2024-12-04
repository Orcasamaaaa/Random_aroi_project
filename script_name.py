import os
import django
import io
from django.core.management import call_command

# กำหนดค่า environment ของ Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ran_domaroi.settings')  # แก้ไขให้ตรงกับชื่อโปรเจกต์ของคุณ

# เริ่มต้น Django
django.setup()

# การ dump ข้อมูล
with io.open('initial_data.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', 'core.Category', 'core.SubCategory', indent=4, stdout=f)
