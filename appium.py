import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Appium TestNG Assistant", page_icon="🧪", layout="centered")
st.title("🧪 Appium Java TestNG Assistant")
st.caption("Your expert for Appium · Java · TestNG · Hybrid Framework issues")

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = os.getenv("OPENROUTER_MODEL", "unknown")

SYSTEM_PROMPT = """You are an expert mobile test automation engineer specialising in:
- Appium (both Appium 1.x and Appium 2.x, all drivers: UiAutomator2, XCUITest, Espresso, Flutter)
- Java (core Java, OOP, lambdas, streams, generics)
- TestNG (annotations, listeners, data providers, parallel execution, suite XML)
- Hybrid Page Object Model (POM) frameworks combining all of the above
- Supporting libraries: Maven/Gradle, ExtentReports, Log4j, Allure, RestAssured, Appium Inspector

When answering:
1. Provide concise, correct, runnable Java/XML/JSON code snippets where applicable.
2. Point out root causes clearly before suggesting a fix.
3. If a stack trace or error message is shared, diagnose it step-by-step.
4. Mention version-specific caveats (e.g. Appium 1 vs 2, TestNG 6 vs 7) when relevant.
5. Keep answers focused on the mobile test automation domain; politely redirect off-topic questions."""

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
    st.markdown("- 📱 Appium 1.x / 2.x")
    st.markdown("- ☕ Java + TestNG")
    st.markdown("- 🏗️ Hybrid POM Framework")
    st.markdown("- 🛠️ Maven · ExtentReports · Log4j")
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
if prompt := st.chat_input("Describe your Appium / TestNG / Java issue..."):
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