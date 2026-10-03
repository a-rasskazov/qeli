/* Regression tests execute the actual embedded components; no DOM or VPN server is required. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const templates = path.join(__dirname, '..', 'qeli', 'src', 'web', 'templates');
let passed = 0;
function component(file, factory, overrides = {}) {
  const html = fs.readFileSync(path.join(templates, file), 'utf8');
  const events = [];
  const context = {
    console, document: { addEventListener() {} }, window: {},
    qeliT: s => s, qeliTf: s => s, qeliConfirm: async () => true,
    apiFetch: async () => ({ ok: true }), fetch: async () => ({ json: async () => ({ ok: false }) }),
    ...overrides,
  };
  vm.createContext(context);
  for (const match of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]).runInContext(context);
  const model = context[factory]();
  model.$dispatch = (...args) => events.push(args);
  return { model, context, events, html };
}
async function check(name, fn) { await fn(); passed++; console.log('PASS ' + name); }
async function main() {
  await check('configuration exposes Form and INI only', async () => {
    const { model, html } = component('config.html', 'configPage');
    assert(!html.includes("switchView('json')"));
    assert(!('onJsonEdit' in model)); assert(!('jsonText' in model));
    await model.switchView('json'); assert.equal(model.view, 'form');
  });
  await check('manual IPv6 preserves NDP across route switches and saves the chosen mode', async () => {
    let sent;
    const { model, html } = component('config.html', 'configPage', {
      apiFetch: async (url, opts) => { sent = JSON.parse(opts.body); return { ok: true, revision: 'r2' }; },
    });
    assert(html.includes('<option value="manual">manual</option>'));
    const routing = { mode: 'route', ndp_proxy: 'required', ndp_proxy_interface: 'ens3' };
    model.cfg = { profiles: [{ tun: { ip_mode: 'dual' }, routing: { ipv6: routing } }] };
    model.loaded = true; model.revision = 'r1';
    model._original = JSON.stringify(model.cfg);
    routing.mode = 'manual'; model.onIpv6RoutingModeChange(0);
    assert.equal(routing.ndp_proxy, 'required'); assert.equal(routing.ndp_proxy_interface, 'ens3');
    await model.save(); assert.equal(sent.config.profiles[0].routing.ipv6.mode, 'manual');
    assert.equal(sent.config.profiles[0].routing.ipv6.ndp_proxy, 'required');
    routing.mode = 'route'; model.onIpv6RoutingModeChange(0); assert.equal(routing.ndp_proxy, 'required');
    for (const mode of ['off', 'nat66']) {
      routing.mode = mode; routing.ndp_proxy = 'required'; routing.ndp_proxy_interface = 'ens3';
      model.onIpv6RoutingModeChange(0);
      assert.equal(routing.ndp_proxy, 'off'); assert.equal(routing.ndp_proxy_interface, '');
    }
    routing.mode = 'manual'; routing.ndp_proxy = 'required';
    model.cfg.profiles[0].tun.ip_mode = 'ipv4'; model.onIpModeChange(0);
    assert.equal(routing.mode, 'off'); assert.equal(routing.ndp_proxy, 'off');
  });
  await check('failed load is visible and blocks writes', async () => {
    let writes = 0;
    const { model, events } = component('config.html', 'configPage', {
      apiFetch: async (url, opts) => { if (opts) writes++; return { ok: false, error: 'fixture read failed' }; },
    });
    model.loadIdentity = () => {};
    await model.load(); assert.equal(model.loaded, false); assert.match(model.loadError, /fixture read failed/);
    assert(events.length); model.dirty = true;
    await model.save(); await model.saveRaw(); await model.applyRestart(); assert.equal(writes, 0);
  });
  await check('reload restores the pending full restart requirement', async () => {
    const { model } = component('config.html', 'configPage', {
      apiFetch: async () => ({ ok: true, config: { profiles: [] }, revision: 'r1', needs_full_restart: true }),
    });
    model.loadIdentity = () => {};
    await model.load(); assert(model.loaded); assert(model.needsFullRestart); assert.equal(model.loadError, '');
  });
  for (const raw of [false, true]) await check((raw ? 'INI' : 'form') + ' keeps edits made during a save dirty', async () => {
    let start, resolve, sent;
    const started = new Promise(r => { start = r; });
    const { model, context } = component('config.html', 'configPage');
    model.loaded = true; model.dirty = true; model.revision = 'r1';
    model.cfg = { profiles: [], logging: { level: 'debug' } };
    model._original = JSON.stringify({ profiles: [], logging: { level: 'info' } });
    model.rawOriginal = 'old'; model.rawText = 'sent';
    context.apiFetch = async (url, opts) => { sent = JSON.parse(opts.body); start(); return new Promise(r => { resolve = r; }); };
    const saving = raw ? model.saveRaw() : model.save(); await started;
    if (raw) model.rawText = 'later'; else model.cfg.logging.level = 'trace';
    model.dirty = true; resolve({ ok: true, revision: 'r2', needs_full_restart: true }); await saving;
    assert(model.dirty); assert.equal(model.revision, 'r2'); assert(model.needsFullRestart);
    assert.equal(raw ? model.rawOriginal : JSON.parse(model._original).logging.level, raw ? 'sent' : 'debug');
    assert.equal(raw ? sent.raw : sent.config.logging.level, raw ? 'sent' : 'debug');
    context.apiFetch = async () => ({ ok: true, revision: 'r3' });
    await (raw ? model.saveRaw() : model.save()); assert(!model.dirty);
  });
  await check('INI socket changes never fall back to worker restart', async () => {
    let workers = 0;
    const { model, events } = component('config.html', 'configPage', {
      apiFetch: async () => ({ ok: true, revision: 'r2', needs_full_restart: true }),
      fullRestartServer: async () => ({ ok: false, kind: 'no_systemd', container: true, error: 'full restart required' }),
      restartServer: async () => { workers++; return true; },
    });
    model.loaded = true; model.view = 'raw'; model.rawOriginal = 'old'; model.rawText = 'new'; model.dirty = true;
    await model.applyRestart(); assert.equal(workers, 0); assert(events.some(e => e[1].type === 'error'));
  });
  await check('failed INI reload remains explicit', async () => {
    const { model } = component('config.html', 'configPage', { apiFetch: async () => ({ ok: false, error: 'unavailable' }) });
    model.loaded = true; await model.loadRaw(); assert(!model.loaded); assert.equal(model.loadError, 'unavailable');
  });
  const keys = ['gateway', 'quic', 'awg', 'autostart', 'route_local', 'allow_ipv4_leak', 'allow_ipv6_leak'];
  for (const literal of ['on', 'YES', 'True', '1', '"ON"']) await check('client INI accepts true spelling ' + literal, () => {
    const { model } = component('client.html', 'clientPage');
    const f = model.blankForm(); model.parseIni('[ qeli ]\nserver=fixture.invalid:443\n' + keys.map(k => `${k}=${literal}`).join('\n'), f);
    assert.equal(f.server, 'fixture.invalid:443'); for (const key of keys) assert.equal(f[key], true, key);
  });
  for (const literal of ['off', 'NO', 'False', '0']) await check('client INI accepts false spelling ' + literal, () => {
    const { model } = component('client.html', 'clientPage');
    const f = model.blankForm(); model.parseIni('[qeli]\nserver=fixture.invalid:443\n' + keys.map(k => `${k}=${literal}`).join('\n'), f);
    for (const key of keys) assert.equal(f[key], false, key);
  });
  await check('removing raw keys clears former field values', () => {
    const { model } = component('client.html', 'clientPage');
    model.form = model.blankForm(); Object.assign(model.form, { name: 'retained', editing: true, pass: 'old', gateway: true, key: 'old-key', rawMode: true, raw: '[qeli]\nserver=fixture.invalid:443\n' });
    model.toggleRaw(); assert.equal(model.form.pass, ''); assert(!model.form.gateway); assert.equal(model.form.key, '');
    assert.equal(model.form.name, 'retained'); assert(model.form.editing); assert(!model.form.rawMode);
  });
  await check('invalid raw input preserves the draft and stays in INI', () => {
    const { model } = component('client.html', 'clientPage'); model.notify = () => {};
    for (const extra of ['gateway=maybe', 'jc=1oops', 'jc=4294967296', 'jmin=65536', 'server=second.invalid:443', '[qeli]']) {
      model.form = model.blankForm(); model.form.rawMode = true; model.form.raw = '[qeli]\nserver=fixture.invalid:443\n' + extra;
      const raw = model.form.raw; model.toggleRaw(); assert(model.form.rawMode); assert.equal(model.form.raw, raw);
    }
  });
  await check('passwords survive Fields to INI to Fields exactly', () => {
    const { model } = component('client.html', 'clientPage');
    for (const secret of ['plain', '"secret"', ' secret ', '\tsecret\t', '\u00a0secret\u00a0', 'a\\b"c', '#;=']) {
      model.form = model.blankForm(); model.form.server = 'fixture.invalid:443'; model.form.pass = secret;
      const ini = model.formToIni(); const f = model.blankForm(); model.parseIni(ini, f); assert.equal(f.pass, secret);
      assert.equal(model.iniValue(model.iniQuote(secret)), secret);
    }
  });
  await check('repeated route lists and non-form sections are retained', () => {
    const { model } = component('client.html', 'clientPage'); const f = model.blankForm();
    model.parseIni('[qeli]\nserver=x:443\ninclude=10.0.0.0/8\ninclude=192.168.0.0/16\nkill_switch=true\n[logging]\nlevel=debug\n', f);
    model.form = f; const text = model.formToIni(); assert(text.includes('include = 10.0.0.0/8, 192.168.0.0/16')); assert(text.includes('kill_switch=true')); assert(text.includes('[logging]\nlevel=debug'));
  });
  await check('changing quota preserves exact expiry; editing or clearing date remains supported', async () => {
    let sent; const { model } = component('users.html', 'usersPage', { apiFetch: async (u, opts) => { sent = JSON.parse(opts.body); return { ok: true }; } });
    model.loadUsage = () => {};
    const expiry = 1790847000;
    model.openUsage('alice', { expire_at: expiry, data_limit_gb: 10 }, 'limit'); model.usageForm.data_limit_gb = 20;
    await model.saveLimit(); assert.equal(sent.expire_at, expiry); assert.equal(sent.data_limit_gb, 20);
    model.usageForm.expire_date = '2026-10-03'; model.syncFromDate(); await model.saveLimit();
    assert.equal(sent.expire_at, Math.floor(new Date('2026-10-03T23:59:59').getTime() / 1000));
    model.usageForm.expire_date = ''; model.syncFromDate(); await model.saveLimit(); assert.equal(sent.expire_at, null);
  });
  await check('shared Rust INI corpus survives the client editor exactly', () => {
    const cases = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'conformance', 'panel-client-ini.json'), 'utf8'));
    const { model } = component('client.html', 'clientPage');
    for (const test of cases) {
      const form = model.blankForm(); model.parseIni(test.raw, form);
      assert.equal(form.pass, test.password);
      model.form = form;
      const line = text => text.split('\n').find(row => row.startsWith('pass = '));
      assert.equal(line(model.formToIni()), line(test.raw));
    }
  });
  await check('notifications cannot save or send a test until initial load succeeds', async () => {
    let finish, writes = 0;
    const { model } = component('notifications.html', 'notificationsPage', {
      apiFetch: async (url, opts) => {
        if (opts) { writes++; return { ok: true }; }
        return new Promise(resolve => { finish = resolve; });
      },
    });
    const loading = model.init();
    await model.save(); await model.testChan('telegram'); assert.equal(writes, 0);
    assert(!model.loaded); assert(model.loading);
    finish({ ok: true, config: { telegram_enabled: true, telegram_token_set: true, telegram_chat_id: 'fixture' } });
    await loading; assert(model.loaded); assert(!model.loading);
    await model.save(); assert.equal(writes, 1);
  });
  await check('failed notification load blocks writes and a successful save retains newer token edits', async () => {
    let writes = 0;
    const { model, context } = component('notifications.html', 'notificationsPage', {
      apiFetch: async (url, opts) => { if (opts) writes++; return { ok: false, error: 'fixture' }; },
    });
    await model.init(); await model.save(); assert.equal(writes, 0); assert(model.loadFailed);
    model.loaded = true; model.loadFailed = false; model.cfg.telegram_token = 'submitted-fixture';
    let finish;
    context.apiFetch = async () => new Promise(resolve => { finish = resolve; });
    const save = model.save(); model.cfg.telegram_token = 'later-fixture';
    finish({ ok: true, config: { telegram_token_set: true } }); await save;
    assert.equal(model.cfg.telegram_token, 'later-fixture');
  });
  await check('lockout policy cannot write before load, after failure, or during another save', async () => {
    let finish, writes = 0;
    const { model, context } = component('blocked.html', 'blockedPage', {
      apiFetch: async (url, opts) => {
        if (opts) { writes++; return { ok: true, revision: 'r2' }; }
        return new Promise(resolve => { finish = resolve; });
      },
    });
    await model.savePolicy(); assert.equal(writes, 0);
    const loading = model.loadPolicy(); await model.savePolicy(); assert.equal(writes, 0);
    finish({ ok: false, error: 'fixture read failed' }); await loading;
    await model.savePolicy(); assert.equal(writes, 0); assert(!model.policyLoaded);
    assert.match(model.policyMsg, /fixture read failed/);
    const retry = model.loadPolicy();
    finish({ ok: true, revision: 'r1', settings: { vpn: { max_attempts: 17 }, panel: { enabled: false } } });
    await retry; assert(model.policyLoaded); assert.equal(model.policy.vpn.max_attempts, 17);
    context.apiFetch = async () => { writes++; return new Promise(resolve => { finish = resolve; }); };
    const save = model.savePolicy(); await model.savePolicy(); assert.equal(writes, 1);
    finish({ ok: true, revision: 'r2', panel_applied: true }); await save;
    assert.equal(model.policyRevision, 'r2'); assert(!model.savingPolicy);
  });
  await check('lockout settings without a revision remain read-only', async () => {
    let writes = 0;
    const { model } = component('blocked.html', 'blockedPage', {
      apiFetch: async (url, opts) => {
        if (opts) writes++;
        return { ok: true, settings: { vpn: { max_attempts: 7 } } };
      },
    });
    await model.loadPolicy(); await model.savePolicy(); assert(!model.policyLoaded); assert.equal(writes, 0);
  });
  await check('unavailable canonical defaults never create a fallback profile and recover on reload', async () => {
    let defaults = { ok: false, error: 'fixture defaults failed' };
    const { model, context } = component('config.html', 'configPage', {
      apiFetch: async url => url.endsWith('/defaults') ? defaults : { ok: true, revision: 'r1', config: { profiles: [] } },
      fetch: async () => ({ json: async () => defaults }),
    });
    model.loadIdentity = () => {};
    await model.load(); assert(model.loaded); model.addProfile();
    assert.equal(model.cfg.profiles.length, 0); assert(!model.dirty); assert(model.defaultsError);
    defaults = { ok: true, profile: { bind: {}, tun: { ip_mode: 'ipv4' }, pool: {}, dns: {}, extension: { retained: true } } };
    await model.load(); model.addProfile(); assert.equal(model.cfg.profiles.length, 1);
    assert(model.cfg.profiles[0].extension.retained); assert(!model.defaultsError);
    defaults = { ok: false, error: 'second read failed' }; await model.load();
    assert.equal(model.defaultProfile, null); model.addProfile(); assert.equal(model.cfg.profiles.length, 0);
  });

  for (const [file, factory, method, success, dataKey] of [
    ['logs.html', 'logsPage', 'load', { ok: true, lines: ['INFO fresh'], path: '/fresh' }, 'lines'],
    ['transport.html', 'transportHealthPage', 'refresh', { ok: true, profiles: [{ name: 'fresh' }], worker_ok: true }, 'profiles'],
    ['blocked.html', 'blockedPage', 'load', { ok: true, blocked: { vpn: [{ ip: 'fresh', unblock_in_secs: 8 }], panel: [] } }, 'blocked'],
  ]) {
    await check(factory + ' ignores obsolete responses and bounds background polls', async () => {
      const pending = [];
      const { model } = component(file, factory, {
        URLSearchParams, apiFetch: () => new Promise(resolve => pending.push(resolve)),
      });
      const old = model[method](); const fresh = model[method]();
      const background = model[method](true); assert.equal(pending.length, 2, 'a busy background poll must not start another request'); await background;
      pending[0]({ ok: false, error: 'obsolete failure' }); await old;
      assert(model.loading, 'obsolete completion must not clear current spinner');
      pending[1](success); await fresh; assert(!model.loading);
      assert.equal(model.error, '');
      const snapshot = JSON.stringify(model[dataKey]);
      const older = model[method](); const newer = model[method]();
      pending[3](success); await newer;
      pending[2]({ ok: true, lines: ['INFO obsolete'], profiles: [{ name: 'obsolete' }], blocked: { vpn: [], panel: [] } }); await older;
      assert.equal(JSON.stringify(model[dataKey]), snapshot);
    });
    await check(factory + ' preserves data on failure and suppresses writes after destroy', async () => {
      let finish; const cleared = [];
      const { model, context, html } = component(file, factory, {
        URLSearchParams, clearInterval: id => { if (id != null) cleared.push(id); }, apiFetch: async () => success,
      });
      await model[method](); const snapshot = JSON.stringify(model[dataKey]);
      context.apiFetch = async () => ({ ok: false, error: 'fixture unavailable' });
      await model[method](true); assert.match(model.error, /fixture unavailable/);
      assert.equal(JSON.stringify(model[dataKey]), snapshot);
      assert(html.includes('role="alert"'), 'load errors must be visible independently of filtered data');
      context.apiFetch = () => new Promise(resolve => { finish = resolve; });
      const pending = model[method](); model.destroy();
      finish({ ok: true, lines: ['INFO after destroy'], profiles: [], blocked: { vpn: [], panel: [] } }); await pending;
      assert.equal(JSON.stringify(model[dataKey]), snapshot);
      assert(!model.loading); assert.equal(model.pendingLoads, 0);
    });
  }
  await check('log errors are not log entries and cannot disappear under level/search filters', async () => {
    const { model, context, html } = component('logs.html', 'logsPage', {
      URLSearchParams, apiFetch: async () => ({ ok: true, lines: ['ERROR retained'] }),
    });
    await model.load(); model.selectedLevels = ['ERROR']; model.search = 'retained'; model.applyFilter();
    context.apiFetch = async () => ({ ok: false, error: 'Session expired' });
    await model.load(); assert.equal(model.filtered.length, 1); assert.match(model.error, /Session expired/);
    assert(html.includes('loaded && !loading && !error && filtered.length === 0'));
  });
  await check('blocked countdown cannot turn a stale snapshot into authoritative empty state', async () => {
    const { model, context, html } = component('blocked.html', 'blockedPage', {
      apiFetch: async () => ({ ok: true, blocked: { vpn: [{ ip: 'fixture', unblock_in_secs: 1 }], panel: [] } }),
    });
    await model.load(); model.tick(); model.tick();
    assert.equal(model.blocked.vpn.length, 1); assert.equal(model.blocked.vpn[0].unblock_in_secs, 0);
    context.apiFetch = async () => ({ ok: false, error: 'fixture unavailable' });
    await model.load(true); model.tick(); assert.equal(model.blocked.vpn.length, 1);
    assert(html.includes('loaded && !loading && !error && blocked.vpn.length === 0'));
    context.apiFetch = async () => ({ ok: true, blocked: { vpn: [], panel: [] } });
    await model.load(); assert.equal(model.blocked.vpn.length, 0); assert.equal(model.error, '');
  });
  await check('polling timers are cleared and cannot start work after destroy', async () => {
    for (const [file, factory] of [['logs.html','logsPage'], ['blocked.html','blockedPage'], ['transport.html','transportHealthPage']]) {
      const callbacks = [], cleared = []; let calls = 0;
      const { model } = component(file, factory, {
        URLSearchParams, setInterval: fn => { callbacks.push(fn); return callbacks.length; },
        clearInterval: id => { if (id != null) cleared.push(id); }, apiFetch: async () => { calls++; return { ok: true, lines: [], blocked: {}, profiles: [] }; },
      });
      model.loadPolicy = async () => {}; model.scrollBottom = () => {};
      if (factory === 'logsPage') { model.autoRefresh = true; model.handleAutoRefresh(); } else await model.init();
      model.destroy(); const before = calls;
      for (const fn of callbacks) fn(); await Promise.resolve();
      assert.equal(calls, before); assert.equal(cleared.length, callbacks.length);
    }
  });
  console.log(`Panel editor regressions: ${passed} passed`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
