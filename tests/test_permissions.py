"""Role-based access control: what regular users and admins may do."""

from app.models import Task, TaskStatus

TASKS = "/api/tasks"


def test_regular_user_cannot_view_another_users_task(
    client, regular_user, other_user, create_task, headers_for
):
    theirs = create_task(other_user, title="Bob's secret")

    response = client.get(f"{TASKS}/{theirs.id}", headers=headers_for(regular_user))

    assert response.status_code == 403
    assert "Bob" not in response.text


def test_regular_user_cannot_edit_another_users_task(
    client, db_session, regular_user, other_user, create_task, headers_for
):
    theirs = create_task(other_user, title="Original")

    response = client.patch(
        f"{TASKS}/{theirs.id}", json={"title": "Hijacked"}, headers=headers_for(regular_user)
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(Task, theirs.id).title == "Original"


def test_regular_user_cannot_update_status_of_own_task(
    client, db_session, regular_user, create_task, headers_for
):
    mine = create_task(regular_user)

    response = client.patch(
        f"{TASKS}/{mine.id}/status", json={"status": "Completed"}, headers=headers_for(regular_user)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    db_session.expire_all()
    assert db_session.get(Task, mine.id).status == TaskStatus.PENDING


def test_regular_user_cannot_update_status_of_another_users_task(
    client, db_session, regular_user, other_user, create_task, headers_for
):
    theirs = create_task(other_user)

    response = client.patch(
        f"{TASKS}/{theirs.id}/status", json={"status": "Testing"}, headers=headers_for(regular_user)
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(Task, theirs.id).status == TaskStatus.PENDING


def test_regular_user_list_never_includes_other_users_tasks(
    client, regular_user, other_user, create_task, headers_for
):
    create_task(other_user, title="not for alice")
    body = client.get(TASKS, headers=headers_for(regular_user)).json()
    assert body["total"] == 0
    assert body["items"] == []


def test_admin_can_view_every_users_tasks(
    client, admin_user, regular_user, other_user, create_task, headers_for
):
    create_task(regular_user, title="alice task")
    create_task(other_user, title="bob task")

    body = client.get(TASKS, headers=headers_for(admin_user)).json()

    assert body["total"] == 2
    assert {item["title"] for item in body["items"]} == {"alice task", "bob task"}


def test_admin_can_view_and_edit_another_users_task(
    client, admin_user, regular_user, create_task, headers_for
):
    task = create_task(regular_user, title="Original")
    headers = headers_for(admin_user)

    assert client.get(f"{TASKS}/{task.id}", headers=headers).status_code == 200

    response = client.patch(
        f"{TASKS}/{task.id}", json={"title": "Edited by admin"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Edited by admin"


def test_admin_can_update_status_of_any_task(
    client, db_session, admin_user, regular_user, create_task, headers_for
):
    task = create_task(regular_user)
    headers = headers_for(admin_user)

    response = client.patch(
        f"{TASKS}/{task.id}/status", json={"status": "In Progress"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"
    db_session.expire_all()
    assert db_session.get(Task, task.id).status == TaskStatus.IN_PROGRESS


def test_admin_status_update_rejects_unknown_status(
    client, admin_user, regular_user, create_task, headers_for
):
    task = create_task(regular_user)
    response = client.patch(
        f"{TASKS}/{task.id}/status", json={"status": "Archived"}, headers=headers_for(admin_user)
    )
    assert response.status_code == 422


def test_admin_status_update_on_missing_task_returns_404(client, admin_user, headers_for):
    response = client.patch(
        f"{TASKS}/424242/status", json={"status": "Completed"}, headers=headers_for(admin_user)
    )
    assert response.status_code == 404


def test_admin_created_tasks_belong_to_the_admin(client, admin_user, headers_for):
    response = client.post(TASKS, json={"title": "Admin task"}, headers=headers_for(admin_user))
    assert response.status_code == 201
    assert response.json()["user_id"] == admin_user.id
