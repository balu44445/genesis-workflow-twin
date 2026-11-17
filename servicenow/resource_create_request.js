// POST /requests body: {"assigned_approver":"<sys_user sys_id>"}
// Requester is always the authenticated user, never a caller-supplied identity.
(function process(request, response) {
    try {
        var body = request.body.data;
        if (!body || Object.keys(body).join(',') !== 'assigned_approver') throw new Error('Invalid body');
        var result = new GenesisGateway().create(body.assigned_approver);
        response.setStatus(201);
        response.setBody(result);
    } catch (e) {
        response.setStatus(400);
        response.setBody({error: 'GENESIS create rejected; check identity, role and configuration'});
    }
})(request, response);
