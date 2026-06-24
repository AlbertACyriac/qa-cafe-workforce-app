import pytest

from app import app, db, seed_database, seed_users


@pytest.fixture()
def client():
    """Create a clean temporary database for every test."""

    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret-key",
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_database()
        seed_users()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(client, username, password):
    """Submit login credentials through the login form."""

    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
        },
        follow_redirects=True,
    )


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"QA Caf" in response.data


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"Login" in response.data


def test_employees_requires_login(client):
    response = client.get(
        "/employees",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please log in to access that page." in response.data
    assert b"Login" in response.data


def test_invalid_login_is_rejected(client):
    response = login(
        client,
        "admin",
        "wrong-password",
    )

    assert response.status_code == 200
    assert b"Invalid username or password." in response.data


def test_admin_can_view_all_sites(client):
    response = login(
        client,
        "admin",
        "Admin123!",
    )

    assert response.status_code == 200
    assert b"Manchester Mainline" in response.data
    assert b"Liverpool Franchise" in response.data
    assert b"Birmingham Mainline" in response.data


def test_liverpool_manager_only_views_liverpool(client):
    response = login(
        client,
        "liverpool_manager",
        "Manager123!",
    )

    assert response.status_code == 200
    assert b"Liverpool Franchise" in response.data
    assert b"Daniel Brown" in response.data
    assert b"Olivia Jones" in response.data

    assert b"Manchester Mainline" not in response.data
    assert b"Birmingham Mainline" not in response.data
    assert b"Amelia Smith" not in response.data


def test_manager_cannot_edit_another_site(client):
    login(
        client,
        "liverpool_manager",
        "Manager123!",
    )

    response = client.get(
        "/employees/1/edit",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        b"You are not authorised to edit that employee."
        in response.data
    )