"""
E2E tests for Group Management workflows - Get and List Groups
"""

from uuid import uuid4


def test_get_and_list_groups_complete_workflow(e2e_client, sso_user_token):
    """
    Complete workflow: Create groups → List all → Get specific → Filter list
    """

    # Step 1: Create a shared group
    create_group_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Engineering Team"},
        cookies={"access_token": sso_user_token["token"]},
    )
    assert create_group_response.status_code == 201
    group_data = create_group_response.json()
    group_id = group_data["id"]

    # Step 2: List all groups (should include personal + shared)
    list_all_response = e2e_client.get(
        "/api/groups?include_personal=true",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert list_all_response.status_code == 200
    all_groups = list_all_response.json()
    assert all_groups["total"] >= 2  # At least personal group + created group
    assert len(all_groups["groups"]) >= 2

    # Verify both personal and shared groups are present
    has_personal = any(g["is_personal"] for g in all_groups["groups"])
    has_shared = any(not g["is_personal"] for g in all_groups["groups"])
    assert has_personal, "Should have at least one personal group"
    assert has_shared, "Should have at least one shared group"

    # Step 3: Get the specific shared group
    get_group_response = e2e_client.get(
        f"/api/groups/{group_id}",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert get_group_response.status_code == 200
    retrieved_group = get_group_response.json()
    assert retrieved_group["id"] == group_id
    assert retrieved_group["name"] == "Engineering Team"
    assert retrieved_group["is_personal"] is False
    assert retrieved_group["user_id"] is None
    # Verify new fields are present
    assert "owners" in retrieved_group
    assert "members" in retrieved_group
    assert isinstance(retrieved_group["owners"], list)
    assert isinstance(retrieved_group["members"], list)
    # The creator should be an owner
    assert sso_user_token["user_id"] in retrieved_group["owners"]

    # Step 4: List only shared groups (exclude personal)
    list_shared_response = e2e_client.get(
        "/api/groups?include_personal=false",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert list_shared_response.status_code == 200
    shared_groups = list_shared_response.json()
    assert shared_groups["total"] >= 1

    # Verify all returned groups are shared (not personal)
    for group in shared_groups["groups"]:
        assert not group["is_personal"], "Should only return shared groups"

    # Verify our created group is in the shared list
    created_group_in_list = any(g["id"] == group_id for g in shared_groups["groups"])
    assert created_group_in_list, "Created group should be in shared groups list"


def test_get_group_not_found(e2e_client, sso_user_token):
    """
    Test getting a non-existent group returns 404
    """
    non_existent_id = uuid4()

    response = e2e_client.get(
        f"/api/groups/{non_existent_id}",
        cookies={"access_token": sso_user_token["token"]},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_group_requires_authentication(e2e_client):
    """
    Test that getting a group requires authentication
    """
    group_id = uuid4()

    response = e2e_client.get(f"/api/groups/{group_id}")

    assert response.status_code == 401


def test_list_groups_requires_authentication(e2e_client):
    """
    Test that listing groups requires authentication
    """
    response = e2e_client.get("/api/groups")

    assert response.status_code == 401


def test_list_groups_with_personal_flag_variations(e2e_client, sso_user_token):
    """
    Test the include_personal flag with different values
    """
    # Create a shared group
    e2e_client.post(
        "/api/groups/",
        json={"name": "Test Group"},
        cookies={"access_token": sso_user_token["token"]},
    )

    # Test with include_personal=true (default)
    response_with_personal = e2e_client.get(
        "/api/groups?include_personal=true",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert response_with_personal.status_code == 200
    with_personal = response_with_personal.json()

    # Test with include_personal=false
    response_without_personal = e2e_client.get(
        "/api/groups?include_personal=false",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert response_without_personal.status_code == 200
    without_personal = response_without_personal.json()

    # Should have more groups when including personal
    assert with_personal["total"] >= without_personal["total"]

    # Test default (should include personal by default)
    response_default = e2e_client.get(
        "/api/groups",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert response_default.status_code == 200
    default = response_default.json()
    assert default["total"] == with_personal["total"]


def test_get_personal_group(e2e_client, sso_user_token):
    """
    Test getting a personal group by its ID
    """
    # List all groups to find the personal group
    list_response = e2e_client.get(
        "/api/groups?include_personal=true",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert list_response.status_code == 200
    all_groups = list_response.json()

    # Find a personal group
    personal_groups = [g for g in all_groups["groups"] if g["is_personal"]]
    assert len(personal_groups) > 0, "Should have at least one personal group"

    personal_group = personal_groups[0]

    # Get the personal group by ID
    get_response = e2e_client.get(
        f"/api/groups/{personal_group['id']}",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["id"] == personal_group["id"]
    assert retrieved["is_personal"] is True
    assert retrieved["user_id"] is not None


def test_get_group_with_owners_and_members(e2e_client, sso_user_token):
    """
    Test that getting a group returns separate lists of owners and members
    """
    # Step 1: Create a shared group (creator is automatically added as owner)
    create_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Test Team"},
        cookies={"access_token": sso_user_token["token"]},
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Step 2: Get the group and verify the response structure includes owners/members
    get_response = e2e_client.get(
        f"/api/groups/{group_id}",
        cookies={"access_token": sso_user_token["token"]},
    )
    assert get_response.status_code == 200
    group = get_response.json()

    # Verify new fields are present in the response
    assert "owners" in group
    assert "members" in group
    assert isinstance(group["owners"], list)
    assert isinstance(group["members"], list)

    # Verify the creator is in owners list
    assert sso_user_token["user_id"] in group["owners"]

    # Verify basic group info
    assert group["id"] == group_id
    assert group["name"] == "Test Team"
    assert group["is_personal"] is False
