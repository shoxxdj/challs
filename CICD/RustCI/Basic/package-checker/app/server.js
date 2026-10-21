'use strict';

const path = require('path');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const http = require('http');
const { spawn } = require('child_process');
const express = require('express');
const { Server } = require('socket.io');
const { validateRepoUrl } = require('./validate');

const PORT = parseInt(process.env.PORT || '3000', 10);
const JOBS_DIR = process.env.JOBS_DIR || path.join(os.tmpdir(), 'pkgchk-jobs');
const MAX_CONCURRENT = parseInt(process.env.MAX_CONCURRENT || '3', 10);
const JOB_TIMEOUT_MS = parseInt(process.env.JOB_TIMEOUT_MS || String(4 * 60 * 1000), 10);
const MAX_LOG_LINES = 2000;

fs.mkdirSync(JOBS_DIR, { recursive: true });

const app = express();
app.disable('x-powered-by');
app.use(express.static(path.join(__dirname, 'public')));
app.get('/healthz', (_req, res) => res.json({ status: 'ok', running }));

const server = http.createServer(app);
const io = new Server(server, { maxHttpBufferSize: 4 * 1024, cors: { origin: false } });

let running = 0;

function rmrf(p) {
  try { fs.rmSync(p, { recursive: true, force: true }); } catch { /* best effort */ }
}

function runJob(socket, url) {
  const id = crypto.randomBytes(6).toString('hex');
  const root = path.join(JOBS_DIR, id);            // cargo install --root
  const target = path.join(JOBS_DIR, `${id}-target`); // build dir
  fs.mkdirSync(root, { recursive: true });

  const emit = (stream, text) => {
    for (const line of String(text).split(/\r?\n/)) {
      if (line.length) socket.emit('log', { stream, line: line.slice(0, 2000) });
    }
  };

  let lines = 0;
  let finished = false;
  const finish = (ok, message) => {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    running--;
    if (ok) {
      emit('info', 'Installation OK');
      emit('info', 'Removing installed package...');
    }
    // uninstall = delete everything this job produced
    rmrf(root);
    rmrf(target);
    if (ok) emit('info', 'Package removed.');
    socket.emit('done', { ok, message, job: id });
    socket.data.busy = false;
  };

  socket.emit('status', { state: 'running', job: id });
  emit('info', `[job ${id}] checking ${url}`);

  // No shell. The URL is a single argv entry and is guaranteed to start with "http".
  const args = [
    'install',
    '--git', url,
    '--root', root,
    '--locked',
    '--color', 'never',
    '--jobs', '2',
  ];
  const child = spawn('cargo', args, {
    cwd: JOBS_DIR,
    env: {
      PATH: process.env.PATH,
      HOME: process.env.HOME,
      CARGO_HOME: process.env.CARGO_HOME,
      RUSTUP_HOME: process.env.RUSTUP_HOME,
      CARGO_TARGET_DIR: target,
      CARGO_TERM_COLOR: 'never',
      CARGO_NET_RETRY: '1',
      GIT_TERMINAL_PROMPT: '0',
      LANG: 'C.UTF-8',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const onData = (stream) => (buf) => {
    if (lines > MAX_LOG_LINES) return;
    const text = buf.toString('utf8');
    lines += text.split('\n').length;
    emit(stream, text);
    if (lines > MAX_LOG_LINES) emit('warn', '... log truncated ...');
  };
  child.stdout.on('data', onData('stdout'));
  child.stderr.on('data', onData('stderr'));

  const timer = setTimeout(() => {
    emit('warn', 'Timeout reached, killing build');
    child.kill('SIGKILL');
  }, JOB_TIMEOUT_MS);

  child.on('error', (err) => {
    emit('stderr', `failed to start cargo: ${err.message}`);
    finish(false, 'Internal error');
  });
  child.on('close', (code, signal) => {
    if (code === 0) finish(true, 'Package installed successfully ✔');
    else finish(false, `Installation failed (${signal || 'exit code ' + code})`);
  });

  socket.on('disconnect', () => { if (!finished) child.kill('SIGKILL'); });
}

io.on('connection', (socket) => {
  socket.data.busy = false;
  socket.emit('hello', { version: require('./package.json').version });

  socket.on('check', (payload) => {
    if (socket.data.busy) return socket.emit('rejected', { error: 'A check is already running' });
    const v = validateRepoUrl(payload && payload.url);
    if (!v.ok) return socket.emit('rejected', { error: v.error });
    if (running >= MAX_CONCURRENT) return socket.emit('rejected', { error: 'Server busy, try again in a moment' });
    socket.data.busy = true;
    running++;
    runJob(socket, v.url);
  });
});

server.listen(PORT, () => console.log(`package-checker listening on :${PORT}`));
