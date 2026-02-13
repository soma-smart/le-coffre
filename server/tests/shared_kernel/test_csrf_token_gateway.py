from uuid import uuid4

from shared_kernel.adapters.secondary import InMemoryCsrfTokenGateway


class TestInMemoryCsrfTokenGateway:
    """Unit tests for InMemoryCsrfTokenGateway."""

    def test_should_generate_unique_tokens_for_different_users(self):
        """Test that different users get different CSRF tokens."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user1_id = uuid4()
        user2_id = uuid4()

        token1 = csrf_gateway.generate_token(user1_id)
        token2 = csrf_gateway.generate_token(user2_id)

        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0

    def test_should_validate_correct_token(self):
        """Test that a valid token is validated successfully."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()
        token = csrf_gateway.generate_token(user_id)

        assert csrf_gateway.validate_token(user_id, token) is True

    def test_should_reject_invalid_token(self):
        """Test that an invalid token is rejected."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()
        csrf_gateway.generate_token(user_id)

        assert csrf_gateway.validate_token(user_id, "invalid_token") is False

    def test_should_reject_token_for_wrong_user(self):
        """Test that a token for one user doesn't work for another user."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user1_id = uuid4()
        user2_id = uuid4()

        token1 = csrf_gateway.generate_token(user1_id)

        assert csrf_gateway.validate_token(user2_id, token1) is False

    def test_should_replace_old_token_when_generating_new_one(self):
        """Test that generating a new token replaces the old one."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()
        old_token = csrf_gateway.generate_token(user_id)
        new_token = csrf_gateway.generate_token(user_id)

        assert old_token != new_token
        assert csrf_gateway.validate_token(user_id, old_token) is False
        assert csrf_gateway.validate_token(user_id, new_token) is True

    def test_should_delete_token_for_user(self):
        """Test that delete_token removes the token for a user."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()
        token = csrf_gateway.generate_token(user_id)

        csrf_gateway.delete_token(user_id)

        assert csrf_gateway.validate_token(user_id, token) is False

    def test_should_not_fail_when_deleting_nonexistent_token(self):
        """Test that deleting a token for a user without a token doesn't fail."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()

        # Should not raise an exception
        csrf_gateway.delete_token(user_id)

    def test_should_return_false_for_user_without_token(self):
        """Test that validating a token for a user without a token returns False."""
        csrf_gateway = InMemoryCsrfTokenGateway()

        user_id = uuid4()

        assert csrf_gateway.validate_token(user_id, "any_token") is False
