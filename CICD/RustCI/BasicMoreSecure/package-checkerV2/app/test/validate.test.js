const assert = require('assert');
const { validateRepoUrl: v } = require('../validate');
const good = ['https://github.com/sharkdp/fd', 'http://gitea:3000/user/repo.git', 'http://10.0.0.5:3000/a/b', 'https://example.com/a/b#branch'];
const bad = ['', '   ', '-h', '--version', 'file:///etc/passwd', 'ssh://git@x/y', 'git://x/y', 'ftp://x/y',
  'https://a/b; id', 'https://a/b && id', 'https://a/b`id`', 'https://a/b$(id)', 'https://a/b c', 'https://a/b\nid',
  "https://a/b'", 'https://a/b"', 'https://github.com', 'https://', 'x'.repeat(400), null, 42, { url: 1 }, 'https://a/b|id', 'https://a/b\\x'];
for (const g of good) assert(v(g).ok, 'should accept ' + g);
for (const b of bad) assert(!v(b).ok, 'should reject ' + JSON.stringify(b));
console.log('validation tests ok');
