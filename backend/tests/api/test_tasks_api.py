from __future__ import annotations

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def _as(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api_client


@pytest.mark.django_db
def test_register_and_me(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "new@example.com", "password": "N0t-a-common-passphrase"},
        format="json",
    )
    assert response.status_code == 201
    token = api_client.post(
        "/api/v1/auth/token/",
        {"email": "new@example.com", "password": "N0t-a-common-passphrase"},
        format="json",
    )
    assert token.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
    me = api_client.get("/api/v1/users/me/")
    assert me.status_code == 200
    assert me.data["email"] == "new@example.com"


@pytest.mark.django_db
def test_register_rejects_common_password(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "weak@example.com", "password": "password123"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_task_lifecycle_and_shared_board(auth_client, user, other_user, api_client):
    create = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Demo", "description": "desc", "assignee_id": str(other_user.id)},
        format="json",
    )
    assert create.status_code == 201
    task_id = create.data["id"]

    _as(api_client, other_user)
    start = api_client.post(f"/api/v1/tasks/{task_id}/start/")
    assert start.status_code == 200
    assert start.data["status"] == "in_progress"

    complete = api_client.post(f"/api/v1/tasks/{task_id}/complete/")
    assert complete.status_code == 200
    assert complete.data["status"] == "done"
    assert complete.data["completed_at"]

    reopen = api_client.post(f"/api/v1/tasks/{task_id}/reopen/")
    assert reopen.status_code == 200
    assert reopen.data["status"] == "todo"
    assert reopen.data["assignee_id"] == str(other_user.id)
    assert reopen.data["completed_at"] is None

    comment = api_client.post(
        f"/api/v1/tasks/{task_id}/comments/",
        {"body": "hello"},
        format="json",
    )
    assert comment.status_code == 201
    assert len(comment.data["comments"]) == 1

    stranger = User.objects.create_user(email="eve@example.com", password="password123")
    _as(api_client, stranger)
    visible = api_client.get(f"/api/v1/tasks/{task_id}/")
    assert visible.status_code == 200
    listed = api_client.get("/api/v1/tasks/")
    assert listed.status_code == 200
    assert any(item["id"] == task_id for item in listed.data["results"])
    assert "comments" not in listed.data["results"][0]

    denied = api_client.post(f"/api/v1/tasks/{task_id}/start/")
    assert denied.status_code == 403
    observer_comment = api_client.post(
        f"/api/v1/tasks/{task_id}/comments/",
        {"body": "from eve"},
        format="json",
    )
    assert observer_comment.status_code == 201


@pytest.mark.django_db
def test_assignee_rules_and_return(auth_client, user, other_user):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Needs owner", "description": "d"},
        format="json",
    )
    task_id = created.data["id"]
    missing = auth_client.post(f"/api/v1/tasks/{task_id}/start/")
    assert missing.status_code == 400

    unknown = auth_client.post(
        f"/api/v1/tasks/{task_id}/assign/",
        {"assignee_id": str(uuid4())},
        format="json",
    )
    assert unknown.status_code == 400

    inactive = User.objects.create_user(email="gone@example.com", password="password123")
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    inactive_response = auth_client.post(
        f"/api/v1/tasks/{task_id}/assign/",
        {"assignee_id": str(inactive.id)},
        format="json",
    )
    assert inactive_response.status_code == 400

    assigned = auth_client.post(
        f"/api/v1/tasks/{task_id}/assign/",
        {"assignee_id": str(other_user.id)},
        format="json",
    )
    assert assigned.status_code == 200
    started = auth_client.post(f"/api/v1/tasks/{task_id}/start/")
    assert started.status_code == 200
    frozen = auth_client.post(
        f"/api/v1/tasks/{task_id}/assign/",
        {"assignee_id": str(user.id)},
        format="json",
    )
    assert frozen.status_code == 400

    returned = auth_client.post(f"/api/v1/tasks/{task_id}/return/")
    assert returned.status_code == 200
    assert returned.data["status"] == "todo"
    assert returned.data["assignee_id"] == str(other_user.id)

    cleared = auth_client.post(
        f"/api/v1/tasks/{task_id}/assign/",
        {"assignee_id": None},
        format="json",
    )
    assert cleared.status_code == 200
    assert cleared.data["assignee_id"] is None

    still_todo = auth_client.delete(f"/api/v1/tasks/{task_id}/")
    assert still_todo.status_code == 204


@pytest.mark.django_db
def test_delete_and_edit_follow_status(auth_client, other_user, api_client):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Locked", "description": "d", "assignee_id": str(other_user.id)},
        format="json",
    )
    task_id = created.data["id"]
    started = auth_client.post(f"/api/v1/tasks/{task_id}/start/")
    blocked = auth_client.delete(f"/api/v1/tasks/{task_id}/")
    assert blocked.status_code == 400

    _as(api_client, other_user)
    text = api_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "Nope", "description": "d", "version": started.data["version"]},
        format="json",
    )
    assert text.status_code == 403

    done = api_client.post(f"/api/v1/tasks/{task_id}/complete/")
    assert done.status_code == 200
    closed = auth_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "Later", "description": "d", "version": done.data["version"]},
        format="json",
    )
    assert closed.status_code == 400

    comment = api_client.post(
        f"/api/v1/tasks/{task_id}/comments/",
        {"body": "done note"},
        format="json",
    )
    assert comment.status_code == 201
    comment_id = comment.data["comments"][-1]["id"]
    stolen = auth_client.delete(f"/api/v1/tasks/{task_id}/comments/{comment_id}/")
    assert stolen.status_code == 403
    removed = api_client.delete(f"/api/v1/tasks/{task_id}/comments/{comment_id}/")
    assert removed.status_code == 200


@pytest.mark.django_db
def test_put_rejects_assignee_and_list_is_paged_in_the_database(auth_client, user, other_user):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Owned", "description": "d", "assignee_id": str(other_user.id)},
        format="json",
    )
    task_id = created.data["id"]
    rejected = auth_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "Owned", "description": "d", "assignee_id": str(user.id)},
        format="json",
    )
    assert rejected.status_code == 400
    assert rejected.data["code"] == "AssigneeChangeNotAllowed"
    kept = auth_client.get(f"/api/v1/tasks/{task_id}/")
    assert kept.data["assignee_id"] == str(other_user.id)

    for index in range(21):
        auth_client.post(
            "/api/v1/tasks/",
            {"title": f"Page {index}", "description": ""},
            format="json",
        )
    with CaptureQueriesContext(connection) as captured:
        first = auth_client.get("/api/v1/tasks/")
    assert first.status_code == 200
    assert first.data["count"] >= 22
    assert len(first.data["results"]) == 20
    assert first.data["next"]
    listed_sql = " ".join(query["sql"] for query in captured.captured_queries)
    assert "LIMIT" in listed_sql.upper()
    second = auth_client.get("/api/v1/tasks/", {"page": 2})
    assert second.status_code == 200
    assert len(second.data["results"]) >= 2
    first_ids = {item["id"] for item in first.data["results"]}
    assert all(item["id"] not in first_ids for item in second.data["results"])


@pytest.mark.django_db
def test_put_requires_the_version_the_client_read(auth_client):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Versioned", "description": "d"},
        format="json",
    )
    task_id = created.data["id"]
    version = created.data["version"]
    saved = auth_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "Versioned", "description": "edited", "version": version},
        format="json",
    )
    assert saved.status_code == 200
    assert saved.data["version"] == version + 1
    stale = auth_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "Too late", "description": "edited", "version": version},
        format="json",
    )
    assert stale.status_code == 409
    assert stale.data["code"] == "TaskConflict"
    missing = auth_client.put(
        f"/api/v1/tasks/{task_id}/",
        {"title": "No version", "description": "edited"},
        format="json",
    )
    assert missing.status_code == 400


@pytest.mark.django_db
def test_notification_stream_frames_one_event(auth_client, api_client, monkeypatch):
    def fake_messages(_user_id):
        yield {"id": "11111111-1111-1111-1111-111111111111", "event_type": "TaskAssigned"}

    monkeypatch.setattr(
        "src.notifications.presentation.stream.iter_redis_messages",
        fake_messages,
    )
    denied = api_client.get("/api/v1/notifications/stream/")
    assert denied.status_code == 401
    response = auth_client.get("/api/v1/notifications/stream/")
    body = b"".join(response.streaming_content).decode()
    assert body.startswith(": connected")
    assert "event: notification" in body
    assert "TaskAssigned" in body


@pytest.mark.django_db
def test_list_rejects_unknown_status_and_schema_is_public(api_client, auth_client):
    bad = auth_client.get("/api/v1/tasks/", {"status": "nope"})
    assert bad.status_code == 400
    long = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Too long", "description": "x" * 4001},
        format="json",
    )
    assert long.status_code == 400
    schema = api_client.get("/api/schema/")
    assert schema.status_code == 200
    docs = api_client.get("/api/docs/")
    assert docs.status_code == 200


@pytest.mark.django_db
def test_notification_read_is_private(
    auth_client, other_user, api_client, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        created = auth_client.post(
            "/api/v1/tasks/",
            {"title": "Notify", "description": "d", "assignee_id": str(other_user.id)},
            format="json",
        )
    assert created.status_code == 201
    _as(api_client, other_user)
    inbox = api_client.get("/api/v1/notifications/me/")
    assert inbox.status_code == 200
    assert inbox.data
    note_id = inbox.data[0]["id"]
    marked = api_client.post(f"/api/v1/notifications/{note_id}/read/")
    assert marked.status_code == 200
    assert marked.data["read_at"]
    hidden = auth_client.post(f"/api/v1/notifications/{note_id}/read/")
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_list_filters_and_missing_task_is_not_found(auth_client, other_user, api_client):
    owned = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Alpha report", "description": "", "assignee_id": str(other_user.id)},
        format="json",
    )
    assert owned.status_code == 201
    started = auth_client.post(f"/api/v1/tasks/{owned.data['id']}/start/")
    assert started.status_code == 200

    _as(api_client, other_user)
    foreign = api_client.post(
        "/api/v1/tasks/",
        {"title": "Beta note", "description": ""},
        format="json",
    )
    assert foreign.status_code == 201

    by_status = auth_client.get("/api/v1/tasks/", {"status": "in_progress"})
    assert {item["id"] for item in by_status.data["results"]} == {owned.data["id"]}

    by_creator = auth_client.get("/api/v1/tasks/", {"creator": str(other_user.id)})
    assert {item["id"] for item in by_creator.data["results"]} == {foreign.data["id"]}

    by_assignee = auth_client.get("/api/v1/tasks/", {"assignee": str(other_user.id)})
    assert owned.data["id"] in {item["id"] for item in by_assignee.data["results"]}

    by_search = auth_client.get("/api/v1/tasks/", {"search": "alpha"})
    assert {item["id"] for item in by_search.data["results"]} == {owned.data["id"]}

    missing = auth_client.get(f"/api/v1/tasks/{uuid4()}/")
    assert missing.status_code == 404
    missing_comment = auth_client.post(
        f"/api/v1/tasks/{uuid4()}/comments/",
        {"body": "gone"},
        format="json",
    )
    assert missing_comment.status_code == 404


@pytest.mark.django_db
def test_author_edits_comment_and_stranger_cannot(auth_client, other_user, api_client):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Notes", "description": ""},
        format="json",
    )
    task_id = created.data["id"]
    commented = auth_client.post(
        f"/api/v1/tasks/{task_id}/comments/",
        {"body": "first"},
        format="json",
    )
    comment_id = commented.data["comments"][-1]["id"]
    edited = auth_client.put(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}/",
        {"body": "second"},
        format="json",
    )
    assert edited.status_code == 200
    assert edited.data["comments"][-1]["body"] == "second"

    _as(api_client, other_user)
    stolen = api_client.put(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}/",
        {"body": "third"},
        format="json",
    )
    assert stolen.status_code == 403
    missing = auth_client.put(
        f"/api/v1/tasks/{task_id}/comments/{uuid4()}/",
        {"body": "nope"},
        format="json",
    )
    assert missing.status_code == 404


@pytest.mark.django_db
def test_register_rejects_duplicate_email_and_login_can_refresh(api_client, user):
    payload = {"email": "new@example.com", "password": "N0t-a-common-passphrase"}
    first = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert first.status_code == 201
    assert first.data["is_staff"] is False
    duplicate = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert duplicate.status_code == 400
    assert duplicate.data["code"] == "EmailAlreadyExists"

    token = api_client.post(
        "/api/v1/auth/token/",
        {"email": user.email, "password": "password123"},
        format="json",
    )
    assert token.status_code == 200
    refreshed = api_client.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": token.data["refresh"]},
        format="json",
    )
    assert refreshed.status_code == 200
    assert refreshed.data["access"]


@pytest.mark.django_db
def test_user_list_hides_inactive_users(auth_client):
    inactive = User.objects.create_user(email="gone@example.com", password="password123")
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    listed = auth_client.get("/api/v1/users/")
    assert listed.status_code == 200
    emails = {item["email"] for item in listed.data}
    assert "alice@example.com" in emails
    assert "gone@example.com" not in emails


@pytest.mark.django_db
def test_admin_can_edit_someone_elses_task(auth_client, api_client):
    created = auth_client.post(
        "/api/v1/tasks/",
        {"title": "Owned", "description": "d"},
        format="json",
    )
    admin = User.objects.create_user(
        email="admin@example.com",
        password="password123",
        is_staff=True,
    )
    _as(api_client, admin)
    updated = api_client.put(
        f"/api/v1/tasks/{created.data['id']}/",
        {"title": "Taken", "description": "d", "version": created.data["version"]},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["title"] == "Taken"


@pytest.mark.django_db
def test_blank_title_is_rejected(auth_client):
    response = auth_client.post(
        "/api/v1/tasks/",
        {"title": "   ", "description": ""},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_notification_stream_keepalive_and_error(auth_client, monkeypatch):
    def fake_messages(_user_id):
        yield None
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "src.notifications.presentation.stream.iter_redis_messages",
        fake_messages,
    )
    response = auth_client.get("/api/v1/notifications/stream/")
    body = b"".join(response.streaming_content).decode()
    assert ": keep-alive" in body
    assert "event: error" in body
    assert response["Cache-Control"] == "no-cache"


@pytest.mark.django_db
def test_healthcheck_reports_ok_and_degraded(api_client, monkeypatch):
    monkeypatch.setattr("django.db.connection.ensure_connection", lambda: None)

    class HealthyRedis:
        def ping(self):
            return True

    monkeypatch.setattr("config.urls.Redis.from_url", lambda _url: HealthyRedis())
    healthy = api_client.get("/health/")
    assert healthy.status_code == 200
    assert healthy.json()["status"] == "ok"
    assert healthy.json()["checks"] == {"database": "ok", "redis": "ok"}

    class DownRedis:
        def ping(self):
            raise ConnectionError("down")

    monkeypatch.setattr("config.urls.Redis.from_url", lambda _url: DownRedis())
    degraded = api_client.get("/health/")
    assert degraded.status_code == 503
    assert degraded.json()["checks"]["redis"] == "error"
