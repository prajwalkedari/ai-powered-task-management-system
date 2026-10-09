"""AI endpoints. Gemini is replaced by httpx.MockTransport, so no network or API key is needed."""

import json
from collections.abc import Callable

import httpx
import pytest

from app.ai.dependencies import get_task_ai_service
from app.ai.gemini_client import GeminiClient
from app.ai.service import TaskAIService
from app.main import app

GENERATE = "/api/tasks/generate-description"
FAKE_KEY = "fake-gemini-key-for-tests"
Handler = Callable[[httpx.Request], httpx.Response]


def gemini_text(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]},
    )


class FakeGemini:
    def __init__(self) -> None:
        self.api_key: str | None = FAKE_KEY
        self.requests: list[httpx.Request] = []
        self.handler: Handler = lambda request: gemini_text('{"description": "Default text."}')

    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)

    def service(self) -> TaskAIService:
        client = GeminiClient(
            api_key=self.api_key,
            model="gemini-test-model",
            base_url="https://gemini.test/v1beta",
            timeout_seconds=5,
            transport=httpx.MockTransport(self._dispatch),
        )
        return TaskAIService(client)


@pytest.fixture
def fake_gemini():
    fake = FakeGemini()
    app.dependency_overrides[get_task_ai_service] = fake.service
    yield fake
    app.dependency_overrides.pop(get_task_ai_service, None)


def test_generate_description_returns_validated_model_output(
    client, regular_user, headers_for, fake_gemini
):
    fake_gemini.handler = lambda request: gemini_text(
        json.dumps({"description": "  Draft the Q3 report covering revenue and churn.  "})
    )

    response = client.post(
        GENERATE, json={"title": "Write Q3 report"}, headers=headers_for(regular_user)
    )

    assert response.status_code == 200
    assert response.json() == {
        "title": "Write Q3 report",
        "description": "Draft the Q3 report covering revenue and churn.",
        "model": "gemini-test-model",
    }
    sent = fake_gemini.requests[0]
    assert sent.headers["x-goog-api-key"] == FAKE_KEY
    prompt = json.loads(sent.content)["contents"][0]["parts"][0]["text"]
    assert "Write Q3 report" in prompt
    assert FAKE_KEY not in response.text


def test_generate_description_requires_authentication_and_makes_no_ai_call(client, fake_gemini):
    response = client.post(GENERATE, json={"title": "Anything"})
    assert response.status_code == 401
    assert fake_gemini.requests == []


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "   "}, {"title": "x" * 201}, {}, {"title": "ok", "model": "other"}],
)
def test_generate_description_validates_the_title(
    client, regular_user, headers_for, fake_gemini, payload
):
    response = client.post(GENERATE, json=payload, headers=headers_for(regular_user))
    assert response.status_code == 422
    assert fake_gemini.requests == []


def test_missing_api_key_returns_503_without_calling_the_provider(
    client, regular_user, headers_for, fake_gemini
):
    fake_gemini.api_key = None

    response = client.post(GENERATE, json={"title": "Anything"}, headers=headers_for(regular_user))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
    assert fake_gemini.requests == []


def test_provider_timeout_returns_504(client, regular_user, headers_for, fake_gemini):
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    fake_gemini.handler = slow
    response = client.post(GENERATE, json={"title": "Slow"}, headers=headers_for(regular_user))

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_timeout"


def test_connection_failure_returns_502(client, regular_user, headers_for, fake_gemini):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    fake_gemini.handler = unreachable
    response = client.post(GENERATE, json={"title": "Offline"}, headers=headers_for(regular_user))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_provider_error"


def test_provider_error_status_does_not_leak_provider_details(
    client, regular_user, headers_for, fake_gemini
):
    fake_gemini.handler = lambda request: httpx.Response(
        500, json={"error": {"message": "internal backend detail XYZ"}}
    )

    response = client.post(GENERATE, json={"title": "Boom"}, headers=headers_for(regular_user))

    assert response.status_code == 502
    assert "XYZ" not in response.text
    assert FAKE_KEY not in response.text


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(200, text="<html>not json</html>"),
        lambda request: httpx.Response(200, json={"error": "no candidates here"}),
        lambda request: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
        lambda request: gemini_text("Sure! Here is a description without JSON."),
        lambda request: gemini_text('{"text": "wrong key"}'),
        lambda request: gemini_text('{"description": "   "}'),
        lambda request: gemini_text(json.dumps({"description": "a" * 1001})),
    ],
)
def test_invalid_provider_output_is_rejected(
    client, regular_user, headers_for, fake_gemini, handler
):
    fake_gemini.handler = handler
    response = client.post(
        GENERATE, json={"title": "Check output"}, headers=headers_for(regular_user)
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_invalid_response"


def test_owner_can_summarise_their_task(
    client, regular_user, create_task, headers_for, fake_gemini
):
    task = create_task(
        regular_user, title="Build login", description="OAuth flow with refresh tokens"
    )
    fake_gemini.handler = lambda request: gemini_text(
        json.dumps({"summary": "Implements OAuth login."})
    )

    response = client.post(f"/api/tasks/{task.id}/summarize", headers=headers_for(regular_user))

    assert response.status_code == 200
    assert response.json() == {
        "task_id": task.id,
        "summary": "Implements OAuth login.",
        "model": "gemini-test-model",
    }
    prompt = json.loads(fake_gemini.requests[0].content)["contents"][0]["parts"][0]["text"]
    assert "OAuth flow with refresh tokens" in prompt


def test_summary_without_description_still_uses_the_title(
    client, regular_user, create_task, headers_for, fake_gemini
):
    task = create_task(regular_user, title="Tidy inbox", description=None)
    fake_gemini.handler = lambda request: gemini_text('{"summary": "Clears the inbox."}')

    response = client.post(f"/api/tasks/{task.id}/summarize", headers=headers_for(regular_user))

    assert response.status_code == 200
    prompt = json.loads(fake_gemini.requests[0].content)["contents"][0]["parts"][0]["text"]
    assert "(no description provided)" in prompt


def test_regular_user_cannot_summarise_another_users_task_and_no_ai_call_is_made(
    client, regular_user, other_user, create_task, headers_for, fake_gemini
):
    theirs = create_task(other_user)

    response = client.post(f"/api/tasks/{theirs.id}/summarize", headers=headers_for(regular_user))

    assert response.status_code == 403
    assert fake_gemini.requests == []


def test_admin_can_summarise_any_task(
    client, admin_user, regular_user, create_task, headers_for, fake_gemini
):
    task = create_task(regular_user)
    fake_gemini.handler = lambda request: gemini_text('{"summary": "Short summary."}')

    response = client.post(f"/api/tasks/{task.id}/summarize", headers=headers_for(admin_user))
    assert response.status_code == 200


def test_summarise_missing_task_returns_404(client, regular_user, headers_for, fake_gemini):
    response = client.post("/api/tasks/777777/summarize", headers=headers_for(regular_user))
    assert response.status_code == 404
    assert fake_gemini.requests == []
