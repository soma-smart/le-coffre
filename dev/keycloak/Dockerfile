# Local-dev Keycloak with the Le Coffre realm baked in.
#
# The realm is COPYied into the image (rather than bind-mounted) so the task
# works both from the host and from inside the dev container via
# docker-outside-of-docker: a relative bind mount would be resolved against the
# host daemon, which has no /app/... path, but a build context is streamed to
# the daemon and therefore works from either location.
FROM quay.io/keycloak/keycloak:26.0
COPY lecoffre-realm.json /opt/keycloak/data/import/lecoffre-realm.json
