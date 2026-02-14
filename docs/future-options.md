# Future Options & Evaluated Alternatives

Evaluated during hackathon (Feb 2026). Documented here to keep options open without cluttering the active architecture.

---

## Hackathon-Possible

### E2B Sandboxed Execution

**What:** Run agent tool calls (Bash, file ops) inside E2B cloud sandboxes instead of on the host.

**Why consider:** Safety for arbitrary code execution, especially if agents generate and run code. The Agent SDK Hosting Guide lists E2B as a supported sandbox provider alongside Modal, Fly Machines, Vercel Sandbox, and Cloudflare Sandboxes.

**Effort:** Medium — E2B has a Python SDK, but wiring it into the Claude Agent SDK's tool execution requires hooks or custom tool wrappers.

**Decision:** Evaluate if time permits on Day 5-6. Not required for demo (we use `bypassPermissions` with no destructive tools).

### Context Engineering Refinements

**What:** Optimize the orchestrator's system prompt, memory loading strategy, and token budgets based on observed behavior.

**Quick wins:**
- Refine system prompt based on actual query patterns (what does the orchestrator do well/poorly?)
- Selective memory loading in `read_product_context` — load relevant sections, not everything
- Better subagent prompts — tune based on observed tool usage patterns

**Decision:** Do incrementally as we test. Not a separate work item.

---

## Post-Hackathon

### SDK Resume (Multi-Turn Context)

**What:** Use `resume=session_id` in `ClaudeAgentOptions` to maintain conversation context across messages.

**Current status:** Broken — SDK returns empty 0-token responses. We submitted [PR #572](https://github.com/anthropics/claude-agent-sdk-python/pull/572) upstream with the buffer deadlock fix. Resume likely needs a separate fix on the CLI side.

**Impact when fixed:** Messages would maintain conversation context. Currently each message is independent (no memory of prior turns within a session, only file-based product memory).

**Action:** Monitor upstream PR. When merged + resume works, update `agent.py` to store `ResultMessage.session_id` and pass it back.

### Recursive Language Models (RLMs)

**What:** A recent paradigm where language models recursively decompose and solve sub-problems, using their own outputs as inputs in structured loops — going beyond single-pass chain-of-thought.

**Relevance:** The orchestrator-subagent pattern in Velocity is already a form of this (orchestrator decomposes → delegates → synthesizes). RLMs formalize it with explicit recursion, potentially enabling deeper multi-step reasoning for complex PM tasks like root-cause analysis or multi-factor prioritization.

**Decision:** Research post-hackathon. Current adaptive thinking + subagent delegation is the practical version for our scope.

### LangGraph + Claude SDK Hybrid

**What:** Use LangGraph for workflow orchestration (conditional branching, state management, routing) while Claude Agent SDK handles execution inside each node.

**Evaluation:** Architecturally interesting but wrong for our case. Our core rule is "Claude Agent SDK IS the orchestrator." Adding LangGraph introduces a second orchestration layer with additional complexity, latency, and state management overhead. The SDK's native `AgentDefinition` + `Task` tool handles our subagent orchestration needs.

**When it might make sense:** If we need 10+ agents with complex conditional routing, human-in-the-loop approval flows, or agents that operate across multiple LLM providers. Not our current scope.

**Reference:** [Khaled Elfakharany's LangGraph + Claude SDK article](https://www.khaledelfakharany.com/articles/langgraph-claude-sdk-integration) — built an 11-agent due diligence platform this way.

### LangSmith Tracing

**What:** Observability into agent runs — trace tool calls, token usage, latency, errors across the full orchestrator + subagent chain.

**Relevance:** Useful for debugging production issues and understanding agent behavior at scale. LangSmith has a Claude Agent SDK integration.

**Decision:** Not needed for hackathon. Worth adding post-launch when we need production observability.

**Reference:** [LangSmith Claude Agent SDK Tracing docs](https://docs.langchain.com/langsmith/trace-claude-agent-sdk)

### claude-agent-server (WebSocket Wrapper)

**What:** [dzhng/claude-agent-server](https://github.com/dzhng/claude-agent-server) (468 stars) — wraps Claude Agent SDK behind a WebSocket server with E2B sandbox support and TypeScript client library.

**Evaluation:** Not a fit for us. We already have FastAPI as the bridge layer with SSE streaming, and our frontend is custom Next.js. Adding a WebSocket wrapper would be an extra abstraction layer.

**When it might make sense:** If we want to offer an embeddable agent API (let others integrate our PM agent into their apps via WebSocket).

### Mem0 / Graph Memory

**What:** Replace file-based product knowledge with Mem0 (Redis-backed) for persistent cross-session memory with automatic extraction and conflict resolution. Add graph memory (Mem0g) for entity relationships.

**Current approach:** File-based markdown in `/memory/` — simple, works for hackathon.

**When to upgrade:** When we need automatic insight extraction, cross-session memory deduplication, or entity relationship tracking (e.g., "which decisions affected which features").

### Vector DB / RAG

**What:** Add Qdrant/Pinecone/Chroma for semantic search over product knowledge, Slack history, Linear tickets.

**Why we skipped it:** See ARCHITECTURE.md Section 5.2. Opus 4.6's 1M context window reduces need for RAG. MCP handles retrieval from source tools. Structured queries beat semantic search for our data.

**When to revisit:** If product knowledge grows beyond what fits in context, or if we need to search across historical data that MCP tools can't access directly.

---

## Resources

- [Agent SDK Hosting Guide](https://platform.claude.com/docs/en/agent-sdk/hosting) — deployment patterns, sandbox providers
- [Claude Code SDK vs LangChain (Skywork AI)](https://skywork.ai/blog/claude-code-sdk-vs-langchain-which-is-better-for-developers/) — validates SDK-native approach
