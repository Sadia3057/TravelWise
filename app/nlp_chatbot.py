"""
TravelWise AI Chatbot
=====================
Powered by NVIDIA NIM API (Free) — LLaMA 3.1 8B model,
no credit card required, 40 requests/min free tier.
"""

import urllib.request
import urllib.error
import json
import sys

# ── Conversation history store (per session key) ──────────────────────────────
_conversation_histories = {}


def _load_api_key() -> str:
    """Load NVIDIA NIM API key from config.py."""
    if 'config' in sys.modules:
        del sys.modules['config']
    try:
        import config as _cfg
        return _cfg.NVIDIA_API_KEY.strip()
    except AttributeError:
        return ""
    except Exception:
        return ""


def _call_nvidia(messages: list, system_prompt: str) -> str:
    """Call NVIDIA NIM API and return the reply text."""
    api_key = _load_api_key()

    if not api_key or api_key.startswith("nvapi-xxx"):
        return (
            "⚠️ NVIDIA API key is not configured.\n\n"
            "Please add your key to config.py:\n"
            "NVIDIA_API_KEY = \"nvapi-your-key-here\"\n\n"
            "Get your free key at: build.nvidia.com"
        )

    # OpenAI-compatible format
    nim_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        nim_messages.append({
            "role":    msg["role"],
            "content": msg["content"]
        })

    payload = json.dumps({
        "model":       "meta/llama-3.1-8b-instruct",
        "messages":    nim_messages,
        "max_tokens":  1024,
        "temperature": 0.7,
        "stream":      False,
    }).encode("utf-8")

    import time

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            try:
                err = json.loads(error_body)
                msg = err.get("message", str(e))
            except Exception:
                msg = str(e)
            if e.code == 401:
                return "❌ Invalid NVIDIA API key. Please check your NVIDIA_API_KEY in config.py."
            if e.code == 429:
                if attempt < 2:
                    time.sleep(5)
                    continue
                return "⚠️ Too many requests. Please wait a few seconds and try again."
            return f"⚠️ Service error ({e.code}): {msg}"
        except Exception as e:
            err_msg = str(e)
            if "timed out" in err_msg or "handshake" in err_msg:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return "⚠️ NVIDIA server is slow to respond. Please try again in a moment."
            return f"Sorry, I'm having trouble connecting right now. ({err_msg})"

    return "⚠️ Could not reach NVIDIA API after 3 attempts. Please try again shortly."


def _build_system_prompt(destinations: list) -> str:
    """Build a system prompt that makes the AI a TravelWise travel expert."""

    dest_lines = []
    for d in destinations:
        dest_lines.append(
            f"{d['name']} ({d['state']}, {d['type']})"
        )
    # Send all destination names so AI knows what's in the app
    dest_context = ", ".join(dest_lines)
    total = len(destinations)

    return f"""You are TravelWise AI, an expert Indian travel assistant embedded in the TravelWise trip planning app.

YOUR PERSONALITY:
- Warm, formal, and knowledgeable — like a professional travel concierge
- Give precise, useful answers — never vague or overly generic
- Use emojis naturally to make responses readable and warm
- Keep responses concise but complete — use bullet points for lists
- Always answer about the SPECIFIC place the user mentions, not all of India

YOUR RULES:
1. If a user asks about a specific place (Kerala, Goa, Manali, etc.) — answer ONLY about that place
2. Never give a generic "all of India" response when a specific place is mentioned
3. If asked "best time to visit Kerala" — answer specifically for Kerala, not other states
4. If asked about budget for Rajasthan — give Rajasthan-specific costs
5. If asked about food in Hyderabad — talk about Hyderabadi food only
6. Always mention practical details: best months, approximate costs, must-do activities
7. For trek/adventure questions, mention difficulty level and preparation needed
8. You only answer travel-related questions about India
9. If asked something non-travel related, politely redirect to travel topics
10. Begin responses warmly but get to the point quickly

TRAVELWISE APP DESTINATIONS (all {total} destinations):
{dest_context}

IMPORTANT: ALL of the above destinations ARE in the TravelWise app. Never say a destination is "not listed" or "not in our app" — if a user asks about any destination above, confirm it is available and answer specifically about it.
Format responses with emojis and bullet points for readability. Keep answers focused and specific."""


def nlp_chatbot_reply(message: str, destinations: list, session_id: str = "default") -> dict:
    """
    Main chatbot function. Returns AI-powered response using NVIDIA NIM.
    Maintains conversation history per session for context.
    """

    if session_id not in _conversation_histories:
        _conversation_histories[session_id] = []

    history = _conversation_histories[session_id]
    history.append({"role": "user", "content": message})

    # Keep last 20 messages to avoid token limits
    if len(history) > 20:
        history = history[-20:]
        _conversation_histories[session_id] = history

    system_prompt = _build_system_prompt(destinations)
    reply = _call_nvidia(history, system_prompt)

    history.append({"role": "assistant", "content": reply})
    _conversation_histories[session_id] = history

    return {
        "reply":      reply,
        "intent":     "ai_response",
        "confidence": 99,
        "entities":   {},
    }


def clear_history(session_id: str = "default"):
    """Clear conversation history for a session."""
    if session_id in _conversation_histories:
        del _conversation_histories[session_id]