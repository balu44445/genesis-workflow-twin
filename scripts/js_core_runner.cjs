// Test adapter only. No ServiceNow host APIs are emulated beyond Class.create().
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({Class: {create: () => function () {}}});
vm.runInContext(fs.readFileSync('servicenow/GenesisCore.js', 'utf8'), context);
const core = new context.GenesisCore();
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = cases.map(c => {
    try {
        return {ok: true, state: c.initial ? core.initial(c.snapshot, c.requester, c.assigned) :
            core.step(c.snapshot, c.state, c.action, c.actor)};
    } catch (error) { return {ok: false}; }
});
process.stdout.write(JSON.stringify(output));
