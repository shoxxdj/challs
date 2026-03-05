#!/usr/bin/env python
"""
Seed script — run once after migrate:
    python seed.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shadowcorp.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from portal.models import Employee

Employee.objects.all().delete()

users = [
    {
        'username':     'admin',
        'email':        'admin@shadowcorp.internal',
        'full_name':    'System Administrator',
        'role':         'admin',
        'department':   'IT Security',
        'password':     'Adm!n_X9#2026',
        'secret_token': 'CTF{0rm_l34k_f1lt3r_1nj3ct10n_ftw}',
        'is_active':    True,
    },
    {
        'username':     'j.martin',
        'email':        'j.martin@shadowcorp.com',
        'full_name':    'Julie Martin',
        'role':         'manager',
        'department':   'Engineering',
        'password':     'JulieM@2024!',
        'secret_token': 'not_your_secret',
        'is_active':    True,
    },
    {
        'username':     'p.dupont',
        'email':        'p.dupont@shadowcorp.com',
        'full_name':    'Pierre Dupont',
        'role':         'employee',
        'department':   'Sales',
        'password':     'Pierre2024',
        'secret_token': 'nothing_here',
        'is_active':    True,
    },
    {
        'username':     'a.nguyen',
        'email':        'a.nguyen@shadowcorp.com',
        'full_name':    'Anh Nguyen',
        'role':         'employee',
        'department':   'Engineering',
        'password':     'Anh_secure99',
        'secret_token': 'move_along',
        'is_active':    False,
    },
]

for u in users:
    token = u.pop('secret_token')
    pwd   = u.pop('password')
    emp   = Employee.objects.create_user(password=pwd, **u)
    emp.secret_token = token
    emp.save()
    print(f"  [+] Created: {emp.username} ({emp.role})")

print("\nDone. Database seeded.")
