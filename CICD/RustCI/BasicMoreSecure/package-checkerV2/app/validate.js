'use strict';

const MAX_LEN = 300;
const ALLOWED_PROTOCOLS = new Set(['http:', 'https:']);

/**
 * Validate that the user input is nothing but a plain http(s) URL.
 * Returns { ok: true, url } with the normalised URL, or { ok: false, error }.
 *
 * The URL is later passed to cargo as a single argv element (no shell),
 * and since it must start with "http" it can never be parsed as an option.
 */
function validateRepoUrl(input) {
  if (typeof input !== 'string') return { ok: false, error: 'URL must be a string' };
  const raw = input.trim();
  if (raw.length === 0) return { ok: false, error: 'URL is empty' };
  if (raw.length > MAX_LEN) return { ok: false, error: `URL too long (max ${MAX_LEN})` };
  // printable ASCII only, no whitespace / control chars / quotes / shell-ish chars
  if (!/^[\x21-\x7e]+$/.test(raw)) return { ok: false, error: 'URL contains forbidden characters' };
  if (/["'`\\<>{}|^$;&*()\[\]]/.test(raw)) return { ok: false, error: 'URL contains forbidden characters' };

  let u;
  try {
    u = new URL(raw);
  } catch {
    return { ok: false, error: 'Not a valid URL' };
  }
  if (!ALLOWED_PROTOCOLS.has(u.protocol)) return { ok: false, error: 'Only http(s) URLs are supported' };
  if (!u.hostname) return { ok: false, error: 'Missing host' };
  if (u.pathname === '/' || u.pathname === '') return { ok: false, error: 'URL must point to a repository' };
  return { ok: true, url: u.toString() };
}

module.exports = { validateRepoUrl };
