"""The CSRF header must be documented, or Swagger offers no way to send it."""


def test_the_openapi_schema_documents_the_csrf_header(unauthenticated_client):
    schema = unauthenticated_client.get("/openapi.json").json()

    assert "CsrfToken" in schema["components"]["securitySchemes"]
    create = schema["paths"]["/iam/service-accounts"]["post"]
    assert any("CsrfToken" in requirement for requirement in create["security"])
