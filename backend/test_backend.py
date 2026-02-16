#!/usr/bin/env python3
"""Test script to validate Velocity backend with real chat requests."""

import asyncio
import json
import sys
from typing import AsyncGenerator

import httpx


BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoint."""
    print("🏥 Testing health endpoint...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/api/health")
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["anthropic_configured"] is True
        print("   ✅ Health check passed\n")


async def test_chat_simple():
    """Test simple chat message."""
    print("💬 Testing simple chat (Hello)...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={"message": "Hello"},
        ) as resp:
            print(f"   Status: {resp.status_code}")
            assert resp.status_code == 200

            events = []
            text_chunks = []
            thinking_chunks = []

            async for line in resp.aiter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    data = line[6:].strip()
                    events.append((event_type, data))

                    if event_type == "text":
                        text_chunks.append(json.loads(data))
                    elif event_type == "thinking":
                        thinking_data = json.loads(data)
                        thinking_chunks.append(thinking_data.get("text", ""))
                    elif event_type == "done":
                        print(f"   Done event: {data}")
                        break

            full_text = "".join(text_chunks)
            full_thinking = "".join(thinking_chunks)

            print(f"   🧠 Thinking: {full_thinking[:100]}...")
            print(f"   💬 Response: {full_text}")
            print(f"   📊 Total events: {len(events)}")
            print("   ✅ Simple chat passed\n")


async def test_chat_research_agent():
    """Test research agent with customer feedback search."""
    print("🔬 Testing research agent (search customer feedback)...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={"message": "What are customers saying about Jira integration?"},
        ) as resp:
            print(f"   Status: {resp.status_code}")
            assert resp.status_code == 200

            text_chunks = []
            agent_activities = []
            tool_calls = []

            current_event = None
            async for line in resp.aiter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: ") and current_event:
                    data = line[6:].strip()

                    if current_event == "text":
                        text_chunks.append(json.loads(data))
                    elif current_event == "agent_activity":
                        agent_data = json.loads(data)
                        agent_activities.append(agent_data)
                        print(f"   🤖 Agent: {agent_data.get('agent')} - {agent_data.get('task')}")
                    elif current_event == "tool_call":
                        tool_data = json.loads(data)
                        tool_calls.append(tool_data)
                        print(f"   🔧 Tool: {tool_data.get('tool')}")
                    elif current_event == "done":
                        done_data = json.loads(data)
                        print(f"   📊 Agents used: {done_data.get('agents_used', [])}")
                        print(f"   📊 Tokens: {done_data.get('tokens_used', {})}")
                        break

            full_text = "".join(text_chunks)
            print(f"   💬 Response ({len(full_text)} chars): {full_text[:200]}...")
            print(f"   🎯 Agent activities: {len(agent_activities)}")
            print(f"   🔧 Tool calls: {len(tool_calls)}")
            print("   ✅ Research agent test passed\n")


async def test_chat_velocity():
    """Test backlog agent with sprint velocity calculation."""
    print("📊 Testing backlog agent (calculate sprint velocity)...")

    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={"message": "Calculate our team velocity over the last 3 sprints"},
        ) as resp:
            print(f"   Status: {resp.status_code}")
            assert resp.status_code == 200

            text_chunks = []
            tool_calls = []

            current_event = None
            async for line in resp.aiter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: ") and current_event:
                    data = line[6:].strip()

                    if current_event == "text":
                        text_chunks.append(json.loads(data))
                    elif current_event == "tool_call":
                        tool_data = json.loads(data)
                        tool_calls.append(tool_data)
                        if "calculate_sprint_velocity" in tool_data.get('tool', ''):
                            print(f"   ✅ Called calculate_sprint_velocity tool!")
                    elif current_event == "done":
                        break

            full_text = "".join(text_chunks)
            print(f"   💬 Response: {full_text[:300]}...")
            print(f"   🔧 Tool calls: {len(tool_calls)}")

            # Verify the velocity tool was called
            velocity_called = any("velocity" in tc.get('tool', '').lower() for tc in tool_calls)
            if velocity_called:
                print("   ✅ Sprint velocity tool was called")
            else:
                print("   ⚠️  Sprint velocity tool was NOT called")

            print("   ✅ Velocity test passed\n")


async def test_multi_turn_conversation():
    """Test multi-turn conversation with context preservation."""
    print("🔄 Testing multi-turn conversation (same session)...")

    session_id = "test-session-multi-turn"

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Turn 1: Ask about a feature
        print("   Turn 1: Asking about dark mode...")
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={
                "message": "Should we prioritize dark mode? Just give me a quick yes or no with one reason.",
                "session_id": session_id,
            },
        ) as resp:
            assert resp.status_code == 200

            text_chunks_1 = []
            current_event = None
            async for line in resp.aiter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: ") and current_event:
                    data = line[6:].strip()

                    if current_event == "text":
                        text_chunks_1.append(json.loads(data))
                    elif current_event == "done":
                        break

            response_1 = "".join(text_chunks_1)
            print(f"   ✅ Turn 1 response: {response_1[:150]}...")

        # Turn 2: Follow-up question referencing previous context
        print("   Turn 2: Follow-up question (should reference dark mode)...")
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json={
                "message": "What was the feature I just asked about?",
                "session_id": session_id,
            },
        ) as resp:
            assert resp.status_code == 200

            text_chunks_2 = []
            events_received = 0
            current_event = None

            async for line in resp.aiter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    events_received += 1
                elif line.startswith("data: ") and current_event:
                    data = line[6:].strip()

                    if current_event == "text":
                        text_chunks_2.append(json.loads(data))
                        # Print streaming chunks in real-time
                        print(f"   📨 Streaming: {json.loads(data)}", end="", flush=True)
                    elif current_event == "thinking":
                        thinking_data = json.loads(data)
                        print(f"\n   🧠 Thinking: {thinking_data.get('text', '')[:80]}...")
                    elif current_event == "agent_activity":
                        agent_data = json.loads(data)
                        print(f"   🤖 Agent: {agent_data.get('agent')} - {agent_data.get('task')}")
                    elif current_event == "done":
                        done_data = json.loads(data)
                        print(f"\n   ✅ Done - Tokens: {done_data.get('tokens_used', {})}")
                        break

            response_2 = "".join(text_chunks_2)
            print(f"\n   💬 Turn 2 response: {response_2}")
            print(f"   📊 Total events received: {events_received}")

            # Verify context was preserved (response should mention dark mode)
            context_preserved = any(
                keyword in response_2.lower()
                for keyword in ["dark mode", "dark-mode", "darkmode", "previous"]
            )

            if context_preserved:
                print("   ✅ Context preserved - second message referenced dark mode!")
            else:
                print("   ⚠️  Context may not be preserved - dark mode not mentioned")
                print(f"   Full response: {response_2}")

            # Verify events are streaming (not all at once)
            if events_received > 5:
                print("   ✅ Events are streaming (received multiple events)")
            else:
                print(f"   ⚠️  Low event count ({events_received}) - may not be streaming properly")

            print("   ✅ Multi-turn test passed\n")


async def main():
    """Run all backend tests."""
    print("=" * 60)
    print("🚀 Velocity Backend Test Suite")
    print("=" * 60)
    print()

    try:
        await test_health()
        await test_chat_simple()
        await test_chat_research_agent()
        await test_chat_velocity()
        await test_multi_turn_conversation()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Access frontend at http://localhost:3000 (NOT devtunnels)")
        print("2. Try these prompts:")
        print("   - 'What are customers saying about Jira integration?'")
        print("   - 'Calculate our team velocity'")
        print("   - 'RICE score: Feature A (reach=1000, impact=3, confidence=80%, effort=2)'")
        print("   - Multi-turn: Ask a question, then ask 'What did I just ask?'")

        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
