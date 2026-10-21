(() => {
  const socket = io();

  const form = document.getElementById('form');
  const input = document.getElementById('url');
  const submit = document.getElementById('submit');
  const errorEl = document.getElementById('error');
  const consoleEl = document.getElementById('console');
  const badge = document.getElementById('badge');

  const LABELS = {
    idle: ['en attente', 'idle'],
    installing: ['installation…', 'running'],
    success: ['installation OK', 'success'],
    cleanup: ['nettoyage…', 'running'],
    failed: ['échec', 'failed'],
  };

  function setBadge(state) {
    const [text, cls] = LABELS[state] || LABELS.idle;
    badge.textContent = text;
    badge.className = `badge ${cls}`;
  }

  function append(text, cls) {
    const span = document.createElement('span');
    if (cls) span.className = cls;
    span.textContent = text + '\n';
    consoleEl.appendChild(span);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    errorEl.hidden = true;
    submit.disabled = true;
    consoleEl.textContent = '';

    socket.emit('check', { url: input.value }, (res) => {
      if (!res || !res.ok) {
        errorEl.textContent = (res && res.error) || 'Erreur inconnue.';
        errorEl.hidden = false;
        submit.disabled = false;
        consoleEl.innerHTML = '<span class="dim">Aucune vérification lancée.</span>';
        setBadge('idle');
      }
    });
  });

  socket.on('log', ({ stream, line }) => {
    let cls = stream === 'stderr' ? 'l-stderr' : '';
    if (line.startsWith('$ ')) cls = 'l-cmd';
    append(line, cls);
  });

  socket.on('status', ({ state, message, reason }) => {
    if (state === 'done') {
      submit.disabled = false;
      return;
    }
    setBadge(state);
    if (state === 'success') append(message, 'l-ok');
    if (state === 'failed') append(`✘ Échec de l'installation (${reason}).`, 'l-err');
  });

  socket.on('disconnect', () => {
    append('— connexion perdue —', 'l-err');
    submit.disabled = false;
  });
})();
