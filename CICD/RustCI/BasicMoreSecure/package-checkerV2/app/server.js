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

const MAX_LISTED_FILES = 1000;
const MAX_SCANNED_FILES = 50000;

/** Parcourt l'arbre sans suivre les symlinks, ignore .git. Retourne les chemins relatifs triés. */
function listFiles(dir) {
  const out = [];
  const stack = [''];
  while (stack.length) {
    const rel = stack.pop();
    let entries;
    try { entries = fs.readdirSync(path.join(dir, rel), { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      if (rel === '' && e.name === '.git') continue;
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) stack.push(r);
      else out.push(r);
      if (out.length > MAX_SCANNED_FILES) return out.sort();
    }
  }
  return out.sort();
}

async function runJob(socket, url) {
  const id = crypto.randomBytes(6).toString('hex');
  const root = path.join(JOBS_DIR, id);               // cargo install --root
  const target = path.join(JOBS_DIR, `${id}-target`); // build dir
  const src = path.join(JOBS_DIR, `${id}-src`);       // git clone
  try {
    fs.mkdirSync(root, { recursive: true });
  } catch (err) {
    console.error('cannot create job dir:', err.message);
    running--;
    socket.data.busy = false;
    return socket.emit('rejected', { error: 'Internal error, try again later' });
  }

  const emit = (stream, text) => {
    for (const line of String(text).split(/\r?\n/)) {
      if (line.length) socket.emit('log', { stream, line: line.slice(0, 2000) });
    }
  };

  let lines = 0;
  let finished = false;
  let child = null;
  let timedOut = false;

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
    rmrf(src);
    if (ok) emit('info', 'Package removed.');
    socket.emit('done', { ok, message, job: id });
    socket.data.busy = false;
  };

  const timer = setTimeout(() => {
    timedOut = true;
    emit('warn', 'Timeout reached, killing build');
    if (child) child.kill('SIGKILL');
  }, JOB_TIMEOUT_MS);

  socket.once('disconnect', () => {
    if (!finished) { timedOut = true; if (child) child.kill('SIGKILL'); finish(false, 'Client disconnected'); }
  });

  /** Lance une commande SANS shell. stream=false => stdout capturé et non affiché. */
  const run = (cmd, args, env, { capture = false } = {}) => new Promise((resolve) => {
    let captured = '';
    child = spawn(cmd, args, { cwd: JOBS_DIR, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const onData = (stream) => (buf) => {
      const text = buf.toString('utf8');
      if (capture && stream === 'stdout') { captured += text; return; }
      if (lines > MAX_LOG_LINES) return;
      lines += text.split('\n').length;
      emit(stream, text);
      if (lines > MAX_LOG_LINES) emit('warn', '... log truncated ...');
    };
    child.stdout.on('data', onData('stdout'));
    child.stderr.on('data', onData('stderr'));
    child.on('error', (err) => { emit('stderr', `failed to start ${cmd}: ${err.message}`); resolve({ code: -1, out: '' }); });
    child.on('close', (code, signal) => resolve({ code, signal, out: captured }));
  });

  const baseEnv = {
    PATH: process.env.PATH,
    HOME: process.env.HOME,
    LANG: 'C.UTF-8',
    GIT_TERMINAL_PROMPT: '0',
  };

  socket.emit('status', { state: 'running', job: id });
  emit('info', `[job ${id}] checking ${url}`);

  try {
    // 1) git clone (http/https uniquement, pas de submodules, symlinks désactivés)
    emit('info', 'Cloning repository...');
    const clone = await run('git', [
      '-c', 'core.symlinks=false',
      'clone', '--depth', '1', '--no-tags', '--single-branch', '--no-recurse-submodules',
      '--', url, src,
    ], { ...baseEnv, GIT_ALLOW_PROTOCOL: 'http:https', GIT_CONFIG_NOSYSTEM: '1' });
    if (finished) return;
    if (clone.code !== 0) return finish(false, timedOut ? 'Timeout' : `Clone failed (${clone.signal || 'exit code ' + clone.code})`);

    // 2) liste des fichiers + recherche de build.rs
    const files = listFiles(src);
    emit('info', `Repository content (${files.length} files):`);
    files.slice(0, MAX_LISTED_FILES).forEach((f) => emit('info', `  ${f}`));
    if (files.length > MAX_LISTED_FILES) emit('info', `  ... and ${files.length - MAX_LISTED_FILES} more`);

    const buildScripts = files.filter((f) => path.posix.basename(f).toLowerCase() === 'build.rs');
    if (buildScripts.length) {
      emit('stderr', 'error: build scripts are not allowed:');
      buildScripts.forEach((f) => emit('stderr', `  ${f}`));
      return finish(false, 'Rejected: build.rs detected');
    }

    // 3) on fige le commit cloné pour que cargo installe exactement ce qui a été vérifié
    const rev = await run('git', ['-C', src, 'rev-parse', 'HEAD'], baseEnv, { capture: true });
    const sha = rev.out.trim();
    if (rev.code !== 0 || !/^[0-9a-f]{40}$/.test(sha)) return finish(false, 'Internal error');
    emit('info', `Pinned to commit ${sha.slice(0, 12)}`);

    // 4) cargo install (pas de shell : l'URL est un seul argv, elle commence par "http")
    const cargo = await run('cargo', [
      'install',
      '--git', url,
      '--rev', sha,
      '--root', root,
      '--locked',
      '--color', 'never',
      '--jobs', '2',
    ], {
      ...baseEnv,
      CARGO_HOME: process.env.CARGO_HOME,
      RUSTUP_HOME: process.env.RUSTUP_HOME,
      CARGO_TARGET_DIR: target,
      CARGO_TERM_COLOR: 'never',
      CARGO_NET_RETRY: '1',
    });
    if (cargo.code === 0) finish(true, 'Package installed successfully ✔');
    else finish(false, timedOut ? 'Timeout' : `Installation failed (${cargo.signal || 'exit code ' + cargo.code})`);
  } catch (err) {
    console.error('job error:', err);
    finish(false, 'Internal error');
  }
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
