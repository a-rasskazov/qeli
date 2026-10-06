// Execute the actual LuCI module with deterministic RPC/UCI fixtures, no browser/router.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../qeli-openwrt/luci-app-qeli/htdocs/luci-static/resources/view/qeli/config.js'), 'utf8');
function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}
function fixture(options = {}) {
    const events = [];
    let staged = '0', committed = '0';
    const context = vm.createContext({
        view: { extend: v => v }, form: {}, poll: {},
        ui: { addNotification() {} }, E: () => ({}), _: v => v,
        rpc: { declare: spec => async action => {
            if (spec.method !== 'service_action') return {};
            events.push(`${action}:${committed}`);
            if (options.failService === action) return false;
            return true;
        } },
        uci: {
            set(a, b, c, value) { staged = value; events.push(`set:${value}`); },
            async save() { events.push('save'); if (options.save) await options.save.promise; },
            async apply() {
                events.push('apply');
                if (options.apply) await options.apply.promise;
                committed = staged;
                events.push(`commit:${committed}`);
                return 0;
            }
        }
    });
    vm.runInContext("String.prototype.format = function(v) { return this.replace('%s',v); };", context);
    vm.runInContext('(function(){' + source.replace('return view.extend({', 'globalThis.audit = { controlService }; return view.extend({') + '\n})()', context);
    return { control: context.audit.controlService, events };
}
async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
(async () => {
    let passed = 0;
    async function test(name, run) { await run(); console.log(`PASS ${name}`); passed++; }
    await test('connect waits for confirmed UCI before enable/start', async () => {
        const apply = deferred(), f = fixture({ apply });
        const request = f.control('connect'); await flush();
        assert.deepEqual(f.events, ['set:1', 'save', 'apply']);
        apply.resolve(); await request;
        assert.deepEqual(f.events, ['set:1', 'save', 'apply', 'commit:1', 'enable:1', 'start:1']);
    });
    await test('disconnect commits disabled intent before stop/disable', async () => {
        const f = fixture(); await f.control('disconnect');
        assert.deepEqual(f.events, ['set:0', 'save', 'apply', 'commit:0', 'stop:0', 'disable:0']);
    });
    await test('failed apply issues no service commands and queue recovers', async () => {
        const apply = deferred(), f = fixture({ apply });
        const request = f.control('connect');
        const rejected = assert.rejects(request, /apply failure/);
        await flush(); apply.reject(new Error('apply failure')); await rejected;
        assert.deepEqual(f.events, ['set:1', 'save', 'apply']);
        await f.control('restart'); assert.equal(f.events.at(-1), 'restart:0');
    });
    await test('failed save issues no apply or service commands', async () => {
        const save = deferred(), f = fixture({ save });
        const rejected = assert.rejects(f.control('connect'), /save failure/);
        await flush(); save.reject(new Error('save failure')); await rejected;
        assert.deepEqual(f.events, ['set:1', 'save']);
    });
    await test('concurrent connect/disconnect/restart preserve whole-operation order', async () => {
        const apply = deferred(), f = fixture({ apply });
        const requests = [f.control('connect'), f.control('disconnect'), f.control('restart')];
        await flush(); assert.deepEqual(f.events, ['set:1', 'save', 'apply']);
        apply.resolve(); await Promise.all(requests);
        assert.deepEqual(f.events, ['set:1', 'save', 'apply', 'commit:1', 'enable:1', 'start:1',
            'set:0', 'save', 'apply', 'commit:0', 'stop:0', 'disable:0', 'restart:0']);
    });
    await test('failed enable stops connect chain and later disconnect works', async () => {
        const f = fixture({ failService: 'enable' });
        await assert.rejects(f.control('connect'), /enable failed/);
        assert.ok(!f.events.includes('start:1'));
        await f.control('disconnect'); assert.equal(f.events.at(-1), 'disable:0');
    });
    await test('unknown action cannot mutate UCI or issue service commands', async () => {
        const f = fixture(); await assert.rejects(f.control('invalid'), /Unknown/);
        assert.deepEqual(f.events, []);
    });
    console.log(`LuCI fixture tests: ${passed} PASS (not rpcd/procd device qualification)`);
})().catch(error => { console.error(error); process.exitCode = 1; });
