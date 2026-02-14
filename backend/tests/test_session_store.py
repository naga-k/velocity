"""Tests for the unified session store API."""

from __future__ import annotations

from app import session_store
from app.models import SessionMessage, SessionResponse


class TestCreateSession:
    async def test_create_with_title(self):
        session = await session_store.create_session("Sprint Planning")
        assert isinstance(session, SessionResponse)
        assert session.title == "Sprint Planning"
        assert session.id
        assert session.message_count == 0

    async def test_create_default_title(self):
        session = await session_store.create_session()
        assert session.title == "Session 1"

    async def test_default_title_increments(self):
        await session_store.create_session()
        s2 = await session_store.create_session()
        assert s2.title == "Session 2"

    async def test_create_returns_utc_timestamp(self):
        session = await session_store.create_session("Test")
        assert session.created_at is not None


class TestGetSession:
    async def test_get_existing(self):
        created = await session_store.create_session("Test")
        fetched = await session_store.get_session(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test"

    async def test_get_nonexistent(self):
        result = await session_store.get_session("does-not-exist")
        assert result is None

    async def test_get_includes_message_count(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "Hello")
        await session_store.save_message(session.id, "assistant", "Hi!")

        fetched = await session_store.get_session(session.id)
        assert fetched is not None
        assert fetched.message_count == 2


class TestListSessions:
    async def test_list_empty(self):
        sessions = await session_store.list_sessions()
        assert sessions == []

    async def test_list_returns_all(self):
        await session_store.create_session("A")
        await session_store.create_session("B")
        sessions = await session_store.list_sessions()
        assert len(sessions) == 2
        titles = {s.title for s in sessions}
        assert titles == {"A", "B"}

    async def test_list_includes_message_counts(self):
        s = await session_store.create_session("Test")
        await session_store.save_message(s.id, "user", "Hello")
        sessions = await session_store.list_sessions()
        assert sessions[0].message_count == 1


class TestDeleteSession:
    async def test_delete_existing(self):
        session = await session_store.create_session("Delete Me")
        assert await session_store.delete_session(session.id) is True
        assert await session_store.get_session(session.id) is None

    async def test_delete_nonexistent(self):
        assert await session_store.delete_session("nope") is False

    async def test_delete_cascades_messages(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "Hello")
        await session_store.delete_session(session.id)
        messages = await session_store.get_messages(session.id)
        assert messages == []


class TestMessages:
    async def test_save_and_retrieve(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "Hello")
        await session_store.save_message(session.id, "assistant", "Hi there!")

        messages = await session_store.get_messages(session.id)
        assert len(messages) == 2
        assert all(isinstance(m, SessionMessage) for m in messages)
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    async def test_messages_ordered_by_time(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "First")
        await session_store.save_message(session.id, "assistant", "Second")
        await session_store.save_message(session.id, "user", "Third")

        messages = await session_store.get_messages(session.id)
        contents = [m.content for m in messages]
        assert contents == ["First", "Second", "Third"]

    async def test_messages_limit(self):
        session = await session_store.create_session("Test")
        for i in range(10):
            await session_store.save_message(session.id, "user", f"Message {i}")

        messages = await session_store.get_messages(session.id, limit=3)
        assert len(messages) == 3

    async def test_messages_empty_session(self):
        session = await session_store.create_session("Empty")
        messages = await session_store.get_messages(session.id)
        assert messages == []


class TestGetSessionContext:
    async def test_context_shape(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "Hello")

        ctx = await session_store.get_session_context(session.id)
        assert "messages" in ctx
        assert "product_context" in ctx
        assert "session_metadata" in ctx

    async def test_context_includes_messages(self):
        session = await session_store.create_session("Test")
        await session_store.save_message(session.id, "user", "Hello")
        await session_store.save_message(session.id, "assistant", "Hi!")

        ctx = await session_store.get_session_context(session.id)
        assert len(ctx["messages"]) == 2
        assert ctx["messages"][0]["role"] == "user"
        assert ctx["messages"][1]["role"] == "assistant"

    async def test_context_includes_metadata(self):
        session = await session_store.create_session("My Session")
        ctx = await session_store.get_session_context(session.id)
        assert ctx["session_metadata"]["title"] == "My Session"
        assert ctx["session_metadata"]["id"] == session.id

    async def test_context_loads_product_context(self):
        session = await session_store.create_session("Test")
        ctx = await session_store.get_session_context(session.id)
        # product_context should be a string (may be empty if file doesn't exist in test)
        assert isinstance(ctx["product_context"], str)

    async def test_context_for_nonexistent_session(self):
        ctx = await session_store.get_session_context("does-not-exist")
        assert ctx["messages"] == []
        assert ctx["session_metadata"] == {}
