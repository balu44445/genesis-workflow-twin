// POST /requests/{id}/actions body: {"action":"submit" | "approve" | "fulfill"}
(function process(request, response) {
    try {
        var body = request.body.data;
        if (!body || Object.keys(body).join(',') !== 'action') throw new Error('Invalid body');
        response.setBody(new GenesisGateway().act(String(request.pathParams.id), body.action));
    } catch (e) {
        response.setStatus(400);
        response.setBody({error: 'GENESIS action rejected by transition guard or configuration check'});
    }
})(request, response);
