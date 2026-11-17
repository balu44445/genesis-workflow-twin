// Global, server-side, scope-only Script Include. Requires the documented unique key.
// Claims are permanent: recovery after an uncertain write is an administrator task.
var GenesisGuard = Class.create();
GenesisGuard.prototype = {
    acquire: function (id, before, after, action, actor) {
        var dictionary = new GlideRecord('sys_dictionary');
        dictionary.addQuery('name', 'u_genesis_action_claim');
        dictionary.addQuery('element', 'u_key');
        dictionary.query();
        if (!dictionary.next() || ['true', '1'].indexOf(dictionary.getValue('unique')) < 0) {
            throw new Error('GENESIS claim key must have a database uniqueness constraint');
        }
        var claim = new GlideRecord('u_genesis_action_claim');
        if (!claim.isValid()) throw new Error('GENESIS claim table is unavailable');
        claim.initialize();
        claim.setValue('u_key', id + ':' + before.state);
        claim.setValue('u_request', id);
        claim.setValue('u_actor', actor);
        claim.setValue('u_action', action);
        claim.setValue('u_before', JSON.stringify(before));
        claim.setValue('u_after', JSON.stringify(after));
        claim.setValue('u_outcome', 'claimed');
        var claimId = claim.insert();
        if (!claimId) throw new Error('GENESIS stage already claimed; refresh or request recovery');
        return String(claimId);
    },

    finish: function (id) {
        var claim = new GlideRecord('u_genesis_action_claim');
        if (!claim.get(id)) throw new Error('GENESIS claim disappeared');
        claim.setValue('u_outcome', 'applied');
        if (!claim.update()) throw new Error('GENESIS claim completion could not be recorded');
    },
    type: 'GenesisGuard'
};
