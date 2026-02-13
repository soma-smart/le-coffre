"""
E2E tests for CSRF protection.
Tests the CSRF middleware and CSRF token endpoint.
"""


class TestCsrfProtection:
    """E2E tests for CSRF protection."""

    def test_should_get_csrf_token_when_authenticated(
        self, authenticated_admin_client, setup
    ):
        """Test that authenticated users can get a CSRF token."""
        response = authenticated_admin_client.get("/api/auth/csrf-token")

        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0

    def test_should_reject_csrf_token_request_when_not_authenticated(
        self, unauthenticated_client
    ):
        """Test that unauthenticated users cannot get a CSRF token."""
        response = unauthenticated_client.get("/api/auth/csrf-token")

        assert response.status_code == 401

    def test_should_allow_post_request_with_valid_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that POST requests with valid CSRF token are allowed."""
        # Get CSRF token
        token_response = authenticated_admin_client.get("/api/auth/csrf-token")
        csrf_token = token_response.json()["csrf_token"]

        # Try to create a group with CSRF token
        group_data = {
            "name": "Test Group with CSRF",
            "description": "Testing CSRF protection",
        }
        response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 201

    def test_should_reject_post_request_without_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that POST requests without CSRF token are rejected."""
        # Disable auto CSRF injection for this test
        authenticated_admin_client.disable_auto_csrf()

        group_data = {
            "name": "Test Group without CSRF",
            "description": "Should fail",
        }
        response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
        )

        # Re-enable auto CSRF for other tests
        authenticated_admin_client.enable_auto_csrf()

        assert response.status_code == 403
        assert "CSRF token missing" in response.json()["detail"]

    def test_should_reject_post_request_with_invalid_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that POST requests with invalid CSRF token are rejected."""
        group_data = {
            "name": "Test Group with invalid CSRF",
            "description": "Should fail",
        }
        response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
            headers={"X-CSRF-Token": "invalid_token_12345"},
        )

        assert response.status_code == 403
        assert "Invalid or expired CSRF token" in response.json()["detail"]

    def test_should_allow_get_request_without_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that GET requests don't require CSRF token."""
        # List groups endpoint
        response = authenticated_admin_client.get("/api/groups")

        # Should work without CSRF token (GET requests are exempt)
        assert response.status_code == 200

    def test_should_reject_put_request_without_csrf_token(
        self, authenticated_admin_client, setup, admin_personal_group_id
    ):
        """Test that PUT requests without CSRF token are rejected."""
        # Disable auto CSRF injection for this test
        authenticated_admin_client.disable_auto_csrf()

        update_data = {
            "name": "Updated Group Name",
            "description": "Updated description",
        }
        response = authenticated_admin_client.put(
            f"/api/groups/{admin_personal_group_id}",
            json=update_data,
        )

        # Re-enable auto CSRF for other tests
        authenticated_admin_client.enable_auto_csrf()

        assert response.status_code == 403
        assert "CSRF token missing" in response.json()["detail"]

    def test_should_reject_delete_request_without_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that DELETE requests without CSRF token are rejected."""
        # First create a group with CSRF token
        token_response = authenticated_admin_client.get("/api/auth/csrf-token")
        csrf_token = token_response.json()["csrf_token"]

        group_data = {
            "name": "Group to Delete",
            "description": "Will be deleted",
        }
        create_response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
            headers={"X-CSRF-Token": csrf_token},
        )
        group_id = create_response.json()["id"]

        # Disable auto CSRF injection
        authenticated_admin_client.disable_auto_csrf()

        # Try to delete without CSRF token
        response = authenticated_admin_client.delete(f"/api/groups/{group_id}")

        # Re-enable auto CSRF
        authenticated_admin_client.enable_auto_csrf()

        assert response.status_code == 403
        assert "CSRF token missing" in response.json()["detail"]

    def test_should_exempt_login_from_csrf_protection(self, e2e_client):
        """Test that login endpoint doesn't require CSRF token."""
        # Register admin first
        register_data = {
            "email": "csrf_test@example.com",
            "password": "password123",
            "display_name": "CSRF Test Admin",
        }
        e2e_client.post("/api/auth/register-admin", json=register_data)

        # Login should work without CSRF token
        login_data = {
            "email": "csrf_test@example.com",
            "password": "password123",
        }
        response = e2e_client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200

    def test_should_exempt_register_from_csrf_protection(self, e2e_client):
        """Test that registration endpoint doesn't require CSRF token."""
        register_data = {
            "email": "csrf_register_test@example.com",
            "password": "password123",
            "display_name": "CSRF Register Test",
        }
        response = e2e_client.post("/api/auth/register-admin", json=register_data)

        assert response.status_code == 201

    def test_should_exempt_refresh_token_from_csrf_protection(
        self, authenticated_admin_client, setup
    ):
        """Test that refresh token endpoint doesn't require CSRF token."""
        # The refresh token endpoint should work without CSRF token
        response = authenticated_admin_client.post("/api/auth/refresh-token")

        # Should succeed or fail for other reasons, but not CSRF
        assert response.status_code != 403 or "CSRF" not in response.json().get(
            "detail", ""
        )

    def test_should_allow_multiple_requests_with_same_csrf_token(
        self, authenticated_admin_client, setup
    ):
        """Test that the same CSRF token can be used for multiple requests."""
        # Get CSRF token
        token_response = authenticated_admin_client.get("/api/auth/csrf-token")
        csrf_token = token_response.json()["csrf_token"]

        # Use it for multiple requests
        for i in range(3):
            group_data = {
                "name": f"Test Group {i}",
                "description": f"Group number {i}",
            }
            response = authenticated_admin_client.post(
                "/api/groups/",
                json=group_data,
                headers={"X-CSRF-Token": csrf_token},
            )
            assert response.status_code == 201

    def test_should_use_new_csrf_token_after_regeneration(
        self, authenticated_admin_client, setup
    ):
        """Test that regenerating a CSRF token invalidates the old one."""
        # Get first CSRF token
        token_response1 = authenticated_admin_client.get("/api/auth/csrf-token")
        csrf_token1 = token_response1.json()["csrf_token"]

        # Get second CSRF token (regenerate)
        token_response2 = authenticated_admin_client.get("/api/auth/csrf-token")
        csrf_token2 = token_response2.json()["csrf_token"]

        assert csrf_token1 != csrf_token2

        # Old token should not work
        group_data = {
            "name": "Test Group with old token",
            "description": "Should fail",
        }
        response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
            headers={"X-CSRF-Token": csrf_token1},
        )
        assert response.status_code == 403

        # New token should work
        group_data = {
            "name": "Test Group with new token",
            "description": "Should succeed",
        }
        response = authenticated_admin_client.post(
            "/api/groups/",
            json=group_data,
            headers={"X-CSRF-Token": csrf_token2},
        )
        assert response.status_code == 201
