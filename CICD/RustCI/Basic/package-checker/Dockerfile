FROM rust:1.90-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        nodejs npm git ca-certificates build-essential gcc make pkg-config libssl-dev util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 -s /usr/sbin/nologin checker
RUN useradd pwned

WORKDIR /srv/app
COPY app/package.json app/package-lock.json ./
RUN npm ci --omit=dev
COPY app/ ./

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# cargo toolchain lives in /usr/local/cargo (root-owned); the checker user gets its own CARGO_HOME
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/home/checker/.cargo \
    HOME=/home/checker \
    JOBS_DIR=/home/checker/jobs \
    PATH=/usr/local/cargo/bin:/usr/local/bin:/usr/bin:/bin
RUN mkdir -p /home/checker/.cargo /home/checker/jobs && chown -R checker:checker /home/checker

COPY user /home
RUN su pwned && cd /home/pwned && gcc -o getflag getflag.c
RUN chown pwned:pwned /home/pwned/flag
RUN chown pwned:pwned /home/pwned/getflag
RUN su pwned && chmod 4755 /home/pwned/getflag
RUN chmod 400 /home/pwned/flag

USER checker
EXPOSE 3000
CMD ["node", "server.js"]
