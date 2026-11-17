// Global, server-side Script Include. Name: GenesisGateway. Client callable: false.
// Privileged, narrowly scoped persistence gateway. Protect table writes with admin ACLs.
// Intentionally uses GlideRecord under explicit authorization; see PDI_SETUP.md.
var GenesisGateway = Class.create();
GenesisGateway.prototype = {
    initialize: function () { this.core = new GenesisCore(); },

    _authorize: function () {
        if (!gs.hasRole('u_genesis_demo')) throw new Error('GENESIS role required');
    },

    _load: function () {
        this._authorize();
        var m = JSON.parse(gs.getProperty('u_genesis.manifest', '{}'));
        m.source = {kind: 'servicenow_export', description: 'Configured GENESIS PDI sample; not inferred platform behavior'};
        this.core.validate(m);
        for (var i = 0; i < m.actors.length; i++) {
            if (!/^[0-9a-f]{32}$/.test(m.actors[i].id)) throw new Error('Configure actual sys_user sys_ids');
            var user = new GlideRecord('sys_user');
            if (!user.get(m.actors[i].id) || user.getValue('active') !== 'true' && user.getValue('active') !== '1') {
                throw new Error('Configured actor missing or inactive');
            }
            var membership = new GlideRecord('sys_user_has_role');
            membership.addQuery('user', m.actors[i].id);
            membership.addQuery('role.name', 'u_genesis_demo');
            membership.setLimit(1);
            membership.query();
            if (!membership.next()) throw new Error('Configured actor lacks u_genesis_demo role');
        }
        return m;
    },

    exportModel: function () { return this._load(); },

    _state: function (record) {
        return {state: record.getValue('u_state'), requester: record.getValue('u_requester'),
            assigned_approver: record.getValue('u_assigned_approver'), approved_by: record.getValue('u_approved_by') || null};
    },

    _writeState: function (record, state) {
        record.setValue('u_state', state.state);
        record.setValue('u_requester', state.requester);
        record.setValue('u_assigned_approver', state.assigned_approver);
        record.setValue('u_approved_by', state.approved_by || '');
    },

    create: function (assigned) {
        var m = this._load();
        var state = this.core.initial(m, String(gs.getUserID()), assigned);
        var record = new GlideRecord('u_genesis_request');
        record.initialize();
        record.setValue('u_snapshot', JSON.stringify(m));
        this._writeState(record, state);
        var id = record.insert();
        if (!id) throw new Error('Insert failed');
        return {sys_id: String(id), runtime: state};
    },

    act: function (id, action) {
        var m = this._load();
        if (typeof id !== 'string' || !/^[0-9a-f]{32}$/.test(id)) throw new Error('Invalid record ID');
        var record = new GlideRecord('u_genesis_request');
        if (!record.get(id)) throw new Error('Request not found');
        // Immutable configuration per request: changing config requires a new request.
        if (record.getValue('u_snapshot') !== JSON.stringify(m)) throw new Error('Configuration changed; create a new demo request');
        var before = this._state(record);
        var state = this.core.step(m, before, action, String(gs.getUserID()));
        var guard = new GenesisGuard();
        // The database's unique id:stage claim admits one writer for this linear stage.
        // A crash leaves the claim in place and blocks retries rather than guessing.
        var claimId = guard.acquire(id, before, state, action, String(gs.getUserID()));
        var fresh = new GlideRecord('u_genesis_request');
        if (!fresh.get(id) || JSON.stringify(this._state(fresh)) !== JSON.stringify(before) ||
                fresh.getValue('u_snapshot') !== JSON.stringify(m)) {
            throw new Error('Request changed after stage claim; administrator review required');
        }
        record = fresh;
        this._writeState(record, state);
        if (!record.update()) throw new Error('Update failed');
        // If this fails, the action may already be applied. Read persisted state before retrying.
        guard.finish(claimId);
        return {sys_id: id, runtime: state};
    },
    type: 'GenesisGateway'
};
