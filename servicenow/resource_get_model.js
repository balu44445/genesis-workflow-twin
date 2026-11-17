// GET /model. Requires authentication and u_genesis_demo REST ACL.
(function process(request, response) {
    try {
        response.setBody(new GenesisGateway().exportModel());
    } catch (e) {
        response.setStatus(400);
        response.setBody({error: 'GENESIS export rejected; check role, configuration and active actors'});
    }
})(request, response);
