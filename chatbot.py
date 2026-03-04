import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="General AI Chatbot", page_icon="💬", layout="centered")
st.title("💬 General AI Chatbot")
st.caption("Configure your model, credentials, and persona — then start chatting.")

# ── Session defaults ──────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []
if "config_saved" not in st.session_state:
    st.session_state.config_saved = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    with st.form("config_form"):
        st.markdown("**🔗 API Settings**")
        base_url = st.text_input(
            "Base URL",
            value=st.session_state.get("cfg_base_url", "https://openrouter.ai/api/v1"),
            placeholder="https://openrouter.ai/api/v1",
        )
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get("cfg_api_key", ""),
            placeholder="sk-...",
            type="password",
        )
        model = st.text_input(
            "Model",
            value=st.session_state.get("cfg_model", ""),
            placeholder="openai/gpt-4o",
        )

        st.markdown("**🧠 System Prompt**")
        system_prompt = st.text_area(
            "System Prompt",
            value=st.session_state.get(
                "cfg_system_prompt",
                "You are a helpful, accurate, and concise assistant.",
            ),
            height=180,
            placeholder="Describe the assistant's role, tone, and constraints...",
        )

        enable_reasoning = st.checkbox(
            "Enable reasoning (if supported by model)",
            value=st.session_state.get("cfg_enable_reasoning", False),
        )

        max_tokens = st.number_input(
            "Max Tokens (per response)",
            min_value=128,
            max_value=32768,
            value=st.session_state.get("cfg_max_tokens", 2048),
            step=256,
            help="Lower this if you hit 402 credit errors.",
        )

        saved = st.form_submit_button("💾 Save & Apply", type="primary", use_container_width=True)
        if saved:
            st.session_state.cfg_base_url = base_url
            st.session_state.cfg_api_key = api_key
            st.session_state.cfg_model = model
            st.session_state.cfg_system_prompt = system_prompt
            st.session_state.cfg_enable_reasoning = enable_reasoning
            st.session_state.cfg_max_tokens = int(max_tokens)
            # Reset conversation when config changes
            st.session_state.messages = []
            st.session_state.api_messages = (
                [{"role": "system", "content": system_prompt}] if system_prompt.strip() else []
            )
            st.session_state.config_saved = True
            st.rerun()

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        sp = st.session_state.get("cfg_system_prompt", "").strip()
        st.session_state.api_messages = (
            [{"role": "system", "content": sp}] if sp else []
        )
        st.rerun()

    st.divider()
    cfg_model = st.session_state.get("cfg_model", "")
    st.markdown(f"**Model:** `{cfg_model or 'not set'}`")
    st.markdown(f"**Turn(s):** {len(st.session_state.messages) // 2}")

# ── Guard: require config before chatting ────────────────────────────────────
cfg_api_key = st.session_state.get("cfg_api_key", "").strip()
cfg_base_url = st.session_state.get("cfg_base_url", "").strip()
cfg_model = st.session_state.get("cfg_model", "").strip()

if not cfg_api_key or not cfg_base_url or not cfg_model:
    st.info("👈 Fill in your **API Key**, **Base URL**, and **Model** in the sidebar and click **Save & Apply** to start chatting.")
    st.stop()

# Build client from saved config
client = OpenAI(base_url=cfg_base_url, api_key=cfg_api_key)

# Ensure api_messages is seeded if first time after save
if not st.session_state.api_messages:
    sp = st.session_state.get("cfg_system_prompt", "").strip()
    if sp:
        st.session_state.api_messages = [{"role": "system", "content": sp}]

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("reasoning"):
            with st.expander("🧠 View reasoning"):
                st.markdown(msg["reasoning"])

# ── Input ─────────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Type your message..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.api_messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                extra = {}
                if st.session_state.get("cfg_enable_reasoning"):
                    extra = {"reasoning": {"enabled": True}}

                response = client.chat.completions.create(
                    model=cfg_model,
                    messages=st.session_state.api_messages,
                    max_tokens=st.session_state.get("cfg_max_tokens", 2048),
                    **({"extra_body": extra} if extra else {}),
                )
            except Exception as e:
                st.session_state.messages.pop()
                st.session_state.api_messages.pop()
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    st.error("⚠️ Rate limit hit — please wait a moment and try again.")
                elif "402" in err_str:
                    st.error("💳 Insufficient credits — lower the **Max Tokens** value in the sidebar config, or top up your account at https://openrouter.ai/settings/credits")
                else:
                    st.error(f"❌ API error: {e}")
                st.stop()

        response_msg = response.choices[0].message
        content = response_msg.content or ""
        st.markdown(content)

        reasoning_text = None
        if getattr(response_msg, "reasoning_details", None):
            parts = []
            for detail in response_msg.reasoning_details:
                text = getattr(detail, "thinking", None) or getattr(detail, "text", None)
                if text:
                    parts.append(text)
            if parts:
                reasoning_text = "\n\n".join(parts)
                with st.expander("🧠 View reasoning"):
                    st.markdown(reasoning_text)

    st.session_state.messages.append(
        {"role": "assistant", "content": content, "reasoning": reasoning_text}
    )
    api_entry = {"role": "assistant", "content": content}
    if getattr(response_msg, "reasoning_details", None):
        api_entry["reasoning_details"] = response_msg.reasoning_details
    st.session_state.api_messages.append(api_entry)
