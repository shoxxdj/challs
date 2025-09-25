# Dockerfile Ubuntu pour ton challenge
FROM python:3.11-slim

# Variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=0

# Mettre à jour et installer dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    bash \
    gcc \
    build-essential \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour l'application Flask
RUN useradd -m -d /app -s /bin/bash appuser

# Créer un utilisateur pour le CTF
RUN useradd -m -d /home/pwned_user -s /bin/sh pwned_user

# Copier les fichiers du CTF
ADD ./user /home
RUN chmod +rx /home/pwned_user

# Compiler getflag en tant que root puis changer ownership
RUN gcc -o /home/pwned_user/getflag /home/pwned_user/getflag.c \
    && chown pwned_user:pwned_user /home/pwned_user/getflag \
    && chmod 4755 /home/pwned_user/getflag

# Protéger le flag
RUN chown pwned_user:pwned_user /home/pwned_user/flag
RUN chmod 400 /home/pwned_user/flag

# Copier le code de l'application Flask
COPY ./app/ /app
RUN chown -R appuser:appuser /app

# Installer les dépendances Python
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Passer à l'utilisateur non-root pour l'application
USER appuser

EXPOSE 5000

# Lancer gunicorn (3 workers)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "3", "--timeout", "30"]
