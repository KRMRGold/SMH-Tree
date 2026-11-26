"""Image validation, current-turn delivery, remote auditing, and chat resume."""

import base64
import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cogplat.config import Settings
from cogplat.domain.chat import MAX_CHAT_IMAGE_BYTES, ChatImage, ChatRequest
from cogplat.main import create_app


PNG = {
    "media_type": "image/png",
    "data": (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+jKXQAAAAASUVORK5CYII="
    ),
}
AUTH = {"Authorization": "Bearer test-token"}


@pytest.mark.parametrize(
    ("media_type", "signature"),
    [
        ("image/png", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", b"\xff\xd8\xff"),
        ("image/webp", b"RIFF\x04\x00\x00\x00WEBP"),
    ],
)
def test_supported_image_signatures(media_type, signature):
    image = ChatImage(media_type=media_type, data=base64.b64encode(signature).decode())
    assert image.byte_count == len(signature)


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"data": "not valid base64"}, "valid base64"),
        ({"data": "iVBORw0KGgp="}, "valid base64"),
        ({"media_type": "image/jpeg"}, "does not match"),
        ({"media_type": "image/gif"}, "Input should be"),
    ],
)
def test_invalid_images_are_rejected(fields, reason):
    with pytest.raises(ValidationError, match=reason):
        ChatImage.model_validate({**PNG, **fields})


def test_image_count_and_decoded_size_limits():
    signature = b"\x89PNG\r\n\x1a\n"
    max_bytes = signature.ljust(MAX_CHAT_IMAGE_BYTES, b"\0")
    max_image = ChatImage(media_type="image/png", data=base64.b64encode(max_bytes).decode())

    with pytest.raises(ValidationError, match="4 MiB"):
        ChatImage(media_type="image/png", data=base64.b64encode(max_bytes + b"\0").decode())

    accepted = ChatRequest(content="Describe", model="fake-model", images=[max_image, max_image])
    assert len(accepted.images) == 2
    with pytest.raises(ValidationError, match="total 8 MiB"):
        ChatRequest(content="Describe", model="fake-model", images=[max_image, max_image, PNG])
    with pytest.raises(ValidationError, match="at most 4"):
        ChatRequest(content="Describe", model="fake-model", images=[PNG] * 5)


class RecordingProvider:
    label = "Fake Vision"
    is_remote = True

    def __init__(self, *, fail_once=False):
        self.calls = []
        self.fail_once = fail_once

    async def stream_chat(self, model, messages, **options):
        self.calls.append(messages)
        if self.fail_once and len(self.calls) == 1:
            raise RuntimeError("temporary provider error")
        yield "Image analysis"


def make_client(tmp_path, provider, *, workflows=True):
    return TestClient(create_app(
        Settings(api_token="test-token", data_dir=tmp_path, workflows_enabled=workflows),
        providers={"fake": provider},
    ))


def create_branch(client):
    response = client.post("/v1/conversations", json={"title": "Vision chat"}, headers=AUTH)
    assert response.status_code == 201
    return response.json()["root_branch_id"]


def event_run_id(response, event):
    assert response.status_code == 200
    expected_prefix = f"event: {event}\ndata: "
    for frame in response.text.split("\n\n"):
        if frame.startswith(expected_prefix):
            return json.loads(frame[len(expected_prefix):])["run_id"]
    pytest.fail(f"Expected {event} event in {response.text}")


@pytest.mark.parametrize("workflows", [False, True], ids=["legacy", "workflow"])
def test_image_is_current_turn_only_and_audited(tmp_path, workflows):
    provider = RecordingProvider()
    client = make_client(tmp_path, provider, workflows=workflows)
    branch_id = create_branch(client)
    chat_path = f"/v1/branches/{branch_id}/chat"
    content = "Describe the attached image. " + "Image question details. " * 1300
    payload = {"content": content, "provider": "fake", "model": "fake-model", "images": [PNG]}

    denied = client.post(chat_path, json=payload, headers=AUTH)
    assert denied.status_code == 403
    assert not provider.calls

    invalid = client.post(
        chat_path,
        json={**payload, "images": [{**PNG, "media_type": "image/jpeg"}], "allow_remote": True},
        headers=AUTH,
    )
    assert invalid.status_code == 422
    assert not provider.calls

    first = client.post(chat_path, json={**payload, "allow_remote": True}, headers=AUTH)
    first_run = event_run_id(first, "done")
    messages = provider.calls[0]
    assert [image.model_dump() for image in messages[-1].images] == [PNG]
    assert all(not message.images for message in messages[:-1])

    packet = client.get(f"/v1/runs/{first_run}/context", headers=AUTH).json()["packet"]
    assert packet["image_count"] == 1
    assert packet["messages"][-1] == {"role": "user", "content": messages[-1].content}
    assert any(item["type"] == "head_tail_truncation" for item in packet["transformations"])
    assert all("images" not in message for message in packet["messages"])
    canonical_messages = packet["messages"]
    canonical_messages[-1]["images"] = [PNG]
    canonical = json.dumps(
        canonical_messages, ensure_ascii=False, separators=(",", ":"),
    ).encode()
    with sqlite3.connect(tmp_path / "app.db") as connection:
        row = connection.execute(
            "SELECT byte_count, packet_sha256 FROM remote_transmissions WHERE run_id = ?",
            (first_run,),
        ).fetchone()
    assert row == (len(canonical), hashlib.sha256(canonical).hexdigest())

    second = client.post(
        chat_path,
        json={"content": "Follow up", "provider": "fake", "model": "fake-model", "allow_remote": True},
        headers=AUTH,
    )
    second_run = event_run_id(second, "done")
    assert all(not message.images for message in provider.calls[1])
    second_packet = client.get(f"/v1/runs/{second_run}/context", headers=AUTH).json()["packet"]
    assert "image_count" not in second_packet
    history = client.get(f"/v1/branches/{branch_id}/messages", headers=AUTH).json()["items"]
    assert [message["content"] for message in history] == [
        content, "Image analysis", "Follow up", "Image analysis",
    ]
    assert all("images" not in message for message in history)


def test_failed_image_chat_resumes_same_packet_after_restart(tmp_path):
    provider = RecordingProvider(fail_once=True)
    client = make_client(tmp_path, provider)
    branch_id = create_branch(client)
    first = client.post(
        f"/v1/branches/{branch_id}/chat",
        json={
            "content": "Analyze the image", "provider": "fake", "model": "fake-model",
            "images": [PNG], "allow_remote": True,
        },
        headers=AUTH,
    )
    run_id = event_run_id(first, "error")
    replacement = RecordingProvider()
    replacement.label = "Different Vision provider"
    changed_client = make_client(tmp_path, replacement)
    blocked = changed_client.post(f"/v1/runs/{run_id}/resume", headers=AUTH)
    assert event_run_id(blocked, "error") == run_id
    assert "change the previously audited remote packet" in blocked.text
    assert not replacement.calls

    restarted = make_client(tmp_path, provider)
    resumed = restarted.post(f"/v1/runs/{run_id}/resume", headers=AUTH)
    assert event_run_id(resumed, "done") == run_id
    assert len(provider.calls) == 2
    assert provider.calls[0] == provider.calls[1]
    assert [image.model_dump() for image in provider.calls[1][-1].images] == [PNG]
    assert len(restarted.get("/v1/transmissions", headers=AUTH).json()["items"]) == 1
    history = restarted.get(f"/v1/branches/{branch_id}/messages", headers=AUTH).json()["items"]
    assert [message["content"] for message in history] == ["Analyze the image", "Image analysis"]
