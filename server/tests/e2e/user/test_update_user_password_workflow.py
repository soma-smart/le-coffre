def test_update_user_password_complete_workflow(e2e_client, setup, client_factory):
    """
    Complete workflow: Update password → Verify old password fails → Verify new password works

    This tests the entire password update lifecycle:
    1. Admin authenticates and gets their user info
    2. Admin updates their password
    3. Verify 204 response
    4. Logout and try to login with OLD password - should fail
    5. Login with NEW password - should succeed
    6. Verify user can access their data with new password
    """
    # Step 1: SETUP - Admin is authenticated via e2e_client and setup fixture
    # Get admin's info
    admin_me_response = e2e_client.get("/api/users/me")
    assert admin_me_response.status_code == 200
    admin_data = admin_me_response.json()
    admin_email = admin_data["email"]
    print(f"Admin authenticated: {admin_email}")

    # Store original password (from setup fixture, the admin has "admin" as password)
    old_password = "admin"
    new_password = "NewSecurePassword123!"

    # Step 2: UPDATE PASSWORD - Admin updates their own password
    update_response = e2e_client.put(
        "/api/users/me/password",
        json={
            "old_password": old_password,
            "new_password": new_password,
        },
    )
    assert update_response.status_code == 204, (
        f"Failed to update password: {update_response.text}"
    )
    print("Password updated successfully")

    # Step 3: VERIFY OLD PASSWORD FAILS - Try to update with wrong old password
    wrong_old_password_response = e2e_client.put(
        "/api/users/me/password",
        json={
            "old_password": old_password,  # This is now wrong
            "new_password": "AnotherPassword456!",
        },
    )
    assert wrong_old_password_response.status_code == 401, (
        "Should fail with wrong old password"
    )
    print("Old password correctly rejected")

    # Step 4: LOGOUT AND TEST OLD PASSWORD - Create new client to test login
    new_client = client_factory()

    # Try to login with OLD password - should fail
    old_password_login_response = new_client.post(
        "/api/auth/login",
        json={
            "email": admin_email,
            "password": old_password,
        },
    )
    assert old_password_login_response.status_code == 401, (
        f"Login with old password should fail but got: {old_password_login_response.status_code}"
    )
    print("Login with old password correctly failed")

    # Step 5: LOGIN WITH NEW PASSWORD - Should succeed
    new_password_login_response = new_client.post(
        "/api/auth/login",
        json={
            "email": admin_email,
            "password": new_password,
        },
    )
    assert new_password_login_response.status_code == 200, (
        f"Login with new password failed: {new_password_login_response.text}"
    )
    print("Login with new password succeeded")

    # Verify access token cookie was set
    access_token = new_password_login_response.cookies.get("access_token")
    assert access_token is not None, "access_token cookie should be set"

    # Step 6: VERIFY SESSION - User can access their data with new credentials
    new_session_me_response = new_client.get("/api/users/me")
    assert new_session_me_response.status_code == 200
    new_session_data = new_session_me_response.json()
    assert new_session_data["email"] == admin_email
    assert new_session_data["id"] == admin_data["id"]
    print(f"New session verified for: {new_session_data['email']}")

    # Step 7: VERIFY CAN UPDATE PASSWORD AGAIN - User can update password multiple times
    another_new_password = "YetAnotherPassword789!"
    update_again_response = new_client.put(
        "/api/users/me/password",
        json={
            "old_password": new_password,
            "new_password": another_new_password,
        },
    )
    assert update_again_response.status_code == 204, (
        "Should be able to update password again"
    )
    print("Password updated again successfully")

    # Step 8: FINAL VERIFICATION - Login with latest password
    final_client = client_factory()
    final_login_response = final_client.post(
        "/api/auth/login",
        json={
            "email": admin_email,
            "password": another_new_password,
        },
    )
    assert final_login_response.status_code == 200
    print("Final verification: Login with latest password succeeded")

    # Verify the second new password works for accessing data
    final_me_response = final_client.get("/api/users/me")
    assert final_me_response.status_code == 200
    assert final_me_response.json()["email"] == admin_email
    print("Complete workflow verified successfully")
