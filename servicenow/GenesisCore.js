// Global, server-side Script Include. Name: GenesisCore. Client callable: false.
// Pure transition semantics: this exact file is also exercised under Node in tests.
var GenesisCore = Class.create();
GenesisCore.prototype = {
    initialize: function () {},

    validate: function (m) {
        function keys(obj, expected) {
            if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('Expected object');
            if (Object.keys(obj).sort().join(',') !== expected.sort().join(',')) throw new Error('Unexpected manifest fields');
        }
        keys(m, ['schema_version', 'semantics', 'workflow_id', 'revision', 'source', 'steps', 'actors', 'policy', 'unsupported_features']);
        if (m.schema_version !== '1' || m.semantics !== 'genesis-sequential-approval/v1') throw new Error('Unsupported semantics');
        if (!Array.isArray(m.steps) || m.steps.join(',') !== 'submit,approve,fulfill') throw new Error('Unsupported steps');
        if (!Array.isArray(m.unsupported_features) || m.unsupported_features.length) throw new Error('Unsupported features');
        if (typeof m.workflow_id !== 'string' || !m.workflow_id || m.workflow_id.length > 100 ||
            typeof m.revision !== 'string' || !m.revision || m.revision.length > 100) throw new Error('Invalid identity');
        keys(m.policy, ['require_distinct_approver']);
        if (typeof m.policy.require_distinct_approver !== 'boolean') throw new Error('Policy must be boolean');
        keys(m.source, ['kind', 'description']);
        if (['fixture', 'servicenow_export'].indexOf(m.source.kind) < 0 ||
            typeof m.source.description !== 'string' || m.source.description.length > 500) throw new Error('Invalid source');
        if (!Array.isArray(m.actors) || m.actors.length < 1 || m.actors.length > 8) throw new Error('Invalid population');
        var ids = {}, seenRoles = {}, i, j, a, roles;
        for (i = 0; i < m.actors.length; i++) {
            a = m.actors[i];
            keys(a, ['id', 'name', 'roles']);
            if (typeof a.id !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(a.id) || ids['id:' + a.id]) throw new Error('Invalid actor ID');
            ids['id:' + a.id] = true;
            if (typeof a.name !== 'string' || !a.name || a.name.length > 100) throw new Error('Invalid actor name');
            if (!Array.isArray(a.roles) || !a.roles.length || a.roles.length > 3) throw new Error('Invalid roles');
            roles = {};
            for (j = 0; j < a.roles.length; j++) {
                if (['requester', 'approver', 'fulfiller'].indexOf(a.roles[j]) < 0 || roles[a.roles[j]]) throw new Error('Invalid role');
                roles[a.roles[j]] = true;
                seenRoles[a.roles[j]] = true;
            }
        }
        if (!seenRoles.requester || !seenRoles.approver || !seenRoles.fulfiller) throw new Error('Missing eligibility');
        return m;
    },

    _eligible: function (m, id, role) {
        for (var i = 0; i < m.actors.length; i++) {
            if (m.actors[i].id === id) return !role || m.actors[i].roles.indexOf(role) >= 0;
        }
        return false;
    },

    initial: function (m, requester, assigned) {
        this.validate(m);
        if (!this._eligible(m, requester, 'requester') || !this._eligible(m, assigned, 'approver')) throw new Error('Ineligible identities');
        return {state: 'draft', requester: requester, assigned_approver: assigned, approved_by: null};
    },

    step: function (m, s, action, actor) {
        this.validate(m);
        if (!this._eligible(m, actor, null)) throw new Error('Unknown actor');
        var next = JSON.parse(JSON.stringify(s));
        if (action === 'submit' && s.state === 'draft' && actor === s.requester) {
            next.state = 'pending';
        } else if (action === 'approve' && s.state === 'pending' && actor === s.assigned_approver &&
                   this._eligible(m, actor, 'approver') && (!m.policy.require_distinct_approver || actor !== s.requester)) {
            next.state = 'approved';
            next.approved_by = actor;
        } else if (action === 'fulfill' && s.state === 'approved' && this._eligible(m, actor, 'fulfiller')) {
            next.state = 'fulfilled';
        } else {
            throw new Error('Transition guard rejected the action');
        }
        return next;
    },
    type: 'GenesisCore'
};
