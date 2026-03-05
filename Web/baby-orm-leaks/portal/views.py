from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password
from django.shortcuts import render
import json

from .models import Employee


# ─────────────────────────────────────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def login_page(request):
    return render(request, 'portal/login.html')


def api_docs(request):
    return render(request, 'portal/api_docs.html')


# ─────────────────────────────────────────────────────────────────────────────
#  VULNERABLE ENDPOINT
#
#  POST /api/login
#  Body: { "filter": { ...any Django ORM kwargs... } }
#
#  The developer thought that letting the client specify which fields to filter
#  on was "flexible". It is. Fatally so.
#
#  Intended (safe) usage:
#      { "filter": { "username": "john.doe", "password": "s3cr3t" } }
#
#  ORM leak attack — bypass password check entirely:
#      { "filter": { "username": "admin", "secret_token__startswith": "CTF{" } }
#
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    filter_kwargs = body.get('filter', {})

    if not isinstance(filter_kwargs, dict) or not filter_kwargs:
        return JsonResponse({'error': 'Missing or invalid filter'}, status=400)

    # Extract plaintext password before passing kwargs to ORM
    # (password is hashed in DB — it must be checked separately)
    plaintext_password = filter_kwargs.pop('password', None)

    try:
        # ⚠️  VULNERABLE: user-controlled kwargs passed directly to filter()
        # An attacker can omit 'password' entirely and filter on any other field,
        # including hidden fields like secret_token.
        user = Employee.objects.filter(**filter_kwargs).first()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    if user is None:
        return JsonResponse({'error': 'Invalid credentials'}, status=403)

    # If a password was provided, verify it properly
    if plaintext_password is not None:
        if not check_password(plaintext_password, user.password):
            return JsonResponse({'error': 'Invalid credentials'}, status=403)

    return JsonResponse(user.public_data, status=200)
