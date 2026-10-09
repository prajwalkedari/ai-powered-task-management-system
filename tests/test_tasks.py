from app.models import Task, TaskStatus

TASKS = "/api/tasks"


def test_create_task_belongs_to_caller_and_starts_pending(client, regular_user, headers_for):
    response = client.post(
        TASKS,
        json={"title": "  Write report  ", "description": "Q3 numbers"},
        headers=headers_for(regular_user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == regular_user.id
    assert body["title"] == "Write report"
    assert body["description"] == "Q3 numbers"
    assert body["status"] == "Pending"
    assert body["created_at"] and body["updated_at"]


def test_create_task_cannot_assign_another_owner(client, regular_user, other_user, headers_for):
    response = client.post(
        TASKS,
        json={"title": "Sneaky", "user_id": other_user.id},
        headers=headers_for(regular_user),
    )
    assert response.status_code == 422


def test_create_task_cannot_set_status(client, regular_user, headers_for):
    response = client.post(
        TASKS,
        json={"title": "Done already", "status": "Completed"},
        headers=headers_for(regular_user),
    )
    assert response.status_code == 422


def test_create_task_requires_a_title(client, regular_user, headers_for):
    response = client.post(
        TASKS, json={"description": "no title"}, headers=headers_for(regular_user)
    )
    assert response.status_code == 422
    fields = [detail["field"] for detail in response.json()["error"]["details"]]
    assert "title" in fields


def test_create_task_requires_authentication(client):
    assert client.post(TASKS, json={"title": "anon"}).status_code == 401


def test_list_returns_only_the_callers_tasks(
    client, regular_user, other_user, create_task, headers_for
):
    create_task(regular_user, title="mine-1")
    create_task(regular_user, title="mine-2")
    create_task(other_user, title="theirs")

    body = client.get(TASKS, headers=headers_for(regular_user)).json()

    assert body["total"] == 2
    assert {item["title"] for item in body["items"]} == {"mine-1", "mine-2"}


def test_list_supports_status_filter_and_pagination(client, regular_user, create_task, headers_for):
    for index in range(5):
        status = TaskStatus.COMPLETED if index >= 3 else TaskStatus.PENDING
        create_task(regular_user, title=f"task-{index}", status=status)
    headers = headers_for(regular_user)

    completed = client.get(TASKS, params={"status": "Completed"}, headers=headers).json()
    assert completed["total"] == 2

    page = client.get(TASKS, params={"skip": 0, "limit": 2}, headers=headers).json()
    assert len(page["items"]) == 2
    assert page["total"] == 5

    assert client.get(TASKS, params={"limit": 0}, headers=headers).status_code == 422
    assert client.get(TASKS, params={"status": "Archived"}, headers=headers).status_code == 422


def test_owner_can_view_their_task(client, regular_user, create_task, headers_for):
    task = create_task(regular_user, title="Mine")
    response = client.get(f"{TASKS}/{task.id}", headers=headers_for(regular_user))
    assert response.status_code == 200
    assert response.json()["title"] == "Mine"


def test_viewing_a_missing_task_returns_404(client, regular_user, headers_for):
    response = client.get(f"{TASKS}/999999", headers=headers_for(regular_user))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_owner_can_edit_title_and_description(client, regular_user, create_task, headers_for):
    task = create_task(regular_user, title="Old", description="Old details")

    response = client.patch(
        f"{TASKS}/{task.id}",
        json={"title": "New title", "description": None},
        headers=headers_for(regular_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New title"
    assert body["description"] is None
    assert body["status"] == "Pending"


def test_edit_requires_at_least_one_field_and_non_null_title(
    client, regular_user, create_task, headers_for
):
    task = create_task(regular_user)
    headers = headers_for(regular_user)

    assert client.patch(f"{TASKS}/{task.id}", json={}, headers=headers).status_code == 422
    assert (
        client.patch(f"{TASKS}/{task.id}", json={"title": None}, headers=headers).status_code == 422
    )


def test_general_edit_cannot_change_status(
    client, db_session, regular_user, create_task, headers_for
):
    task = create_task(regular_user, title="Keep")

    response = client.patch(
        f"{TASKS}/{task.id}",
        json={"title": "Changed", "status": "Completed"},
        headers=headers_for(regular_user),
    )

    assert response.status_code == 422
    db_session.expire_all()
    assert db_session.get(Task, task.id).status == TaskStatus.PENDING
    assert db_session.get(Task, task.id).title == "Keep"
