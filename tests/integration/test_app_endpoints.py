"""Integration tests for application endpoints and basic session handling."""



def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "web-security-control-lab"
    assert "mode" in data


def test_unauthenticated_profile_redirects(client):
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_failure_returns_401(client):
    response = client.post(
        "/login",
        data={"username": "alice", "password": "wrong_password"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.text


def test_login_success_and_profile_access(client):
    # Login as alice
    login_resp = client.post(
        "/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    assert login_resp.headers["location"] == "/profile"
    assert "lab_session" in login_resp.cookies

    # Profile HTML page access
    profile_resp = client.get("/profile")
    assert profile_resp.status_code == 200
    assert "Alice User" in profile_resp.text

    # Profile API endpoint
    api_resp = client.get("/api/profile")
    assert api_resp.status_code == 200
    user_data = api_resp.json()
    assert user_data["username"] == "alice"
    assert user_data["role"] == "user"


def test_logout_clears_session(client):
    # Login first
    client.post(
        "/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )
    # Logout
    logout_resp = client.get("/logout", follow_redirects=False)
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login"

    # Profile should now redirect
    profile_resp = client.get("/profile", follow_redirects=False)
    assert profile_resp.status_code == 303
