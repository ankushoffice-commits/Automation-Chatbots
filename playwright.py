import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Playwright Framework Assistant", page_icon="🎭", layout="centered")
st.title("🎭 Playwright Hybrid Framework Assistant")
st.caption("Your expert for Playwright · Hybrid Framework · Planner · Generator · Healer Agents · MCP")

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = os.getenv("OPENROUTER_MODEL", "unknown")

SYSTEM_PROMPT = """You are an expert test automation architect specialising in a Playwright-based AI-augmented hybrid framework that combines:

## Core Stack
- **Playwright** (TypeScript/JavaScript or Python bindings) — browser automation, fixtures, page objects, API testing
- **Hybrid Framework** — Page Object Model layered with utility helpers, config management, test data factories, and reporting

## AI Agent Layer
- **Planner Agent** — analyses requirements or user stories and plans test scenarios / step sequences; understands intent-to-test mapping
- **Generator Agent** — auto-generates Playwright test code (spec files, page objects, locators) from the planner's output or from UI snapshots/selectors
- **Healer Agent** — detects broken locators or flaky selectors at runtime and self-heals them using fallback strategies (alternative attributes, visual matching, AI re-identification); logs healed selectors back to the codebase
- **Playwright MCP (Model Context Protocol)** — a Playwright-powered MCP server that exposes browser actions (navigate, click, fill, snapshot, evaluate) as tool calls so LLMs can drive the browser directly; understanding of how to configure, invoke, and extend MCP tools in a test pipeline

## Supporting Libraries & Tooling
- **TypeScript** (strict mode, interfaces, generics, decorators)
- **Node.js** ecosystem: npm/yarn, dotenv, ts-node
- **Playwright Test** runner: fixtures, projects, sharding, retries, global setup/teardown
- **Allure / HTML Reporter / Playwright built-in reporter**
- **CI/CD**: GitHub Actions, Docker, environment-based config
- **LLM integration**: OpenAI / OpenRouter API calls inside agents, prompt engineering for test generation and healing

## How to Answer
1. Provide concise, runnable TypeScript/JavaScript (or Python) code snippets where applicable.
2. Clearly state the root cause before suggesting a fix.
3. If a stack trace, error message, or failing selector is shared, diagnose step-by-step.
4. Distinguish between Planner / Generator / Healer concerns so the user knows which agent layer to address.
5. For MCP questions, explain the tool schema, how the LLM invokes it, and how to register/extend tools.
6. Mention version-specific caveats (Playwright v1.x API changes, Node LTS, Appium/Playwright interop) when relevant.
7. Politely redirect questions outside the Playwright hybrid framework + AI agents domain."""

# ── Auth ─────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if username == "ankush" and password == "Automation":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []        # display history (role + content)
if "api_messages" not in st.session_state:
    # Seed with system prompt
    st.session_state.api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🗑️ Clear Chat", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.markdown("**Specialisation**")
    st.markdown("- 🎭 Playwright (TS/JS/Python)")
    st.markdown("- 🏗️ Hybrid POM Framework")
    st.markdown("- 🧠 Planner Agent")
    st.markdown("- ⚙️ Generator Agent")
    st.markdown("- 🩹 Healer Agent")
    st.markdown("- 🔌 Playwright MCP")
    st.divider()
    st.markdown(f"**Model:** `{MODEL}`")
    st.markdown(f"**Turn(s):** {len(st.session_state.messages) // 2}")

# ── Chat history ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("reasoning"):
            with st.expander("🧠 View reasoning"):
                st.markdown(msg["reasoning"])

# ── Input ─────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Describe your Playwright / Agent / MCP issue..."):
    # Show user bubble immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.api_messages.append({"role": "user", "content": prompt})

    # Stream / fetch assistant reply
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=st.session_state.api_messages,
                    extra_body={"reasoning": {"enabled": True}},
                )
            except Exception as e:
                # Roll back the user message so the user can try again
                st.session_state.messages.pop()
                st.session_state.api_messages.pop()
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    st.error("⚠️ Rate limit hit — the model is temporarily busy. Please wait a moment and try again.")
                else:
                    st.error(f"❌ API error: {e}")
                st.stop()

        msg = response.choices[0].message
        content = msg.content or ""
        st.markdown(content)

        # Extract reasoning text if present
        reasoning_text = None
        if getattr(msg, "reasoning_details", None):
            parts = []
            for detail in msg.reasoning_details:
                text = getattr(detail, "thinking", None) or getattr(detail, "text", None)
                if text:
                    parts.append(text)
            if parts:
                reasoning_text = "\n\n".join(parts)
                with st.expander("🧠 View reasoning"):
                    st.markdown(reasoning_text)

    # Persist to history
    st.session_state.messages.append(
        {"role": "assistant", "content": content, "reasoning": reasoning_text}
    )
    api_entry = {"role": "assistant", "content": content}
    if getattr(msg, "reasoning_details", None):
        api_entry["reasoning_details"] = msg.reasoning_details
    st.session_state.api_messages.append(api_entry)