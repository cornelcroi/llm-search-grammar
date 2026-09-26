"""One call to the model. Standard library only; the only thing it needs is OPENAI_API_KEY.

    OPENAI_MODEL   defaults to gpt-6-luna, the smallest current model: parsing against a grammar
                   is classification, not reasoning, and a small model does it well. Reasoning is off.
"""
import json
import os
import ssl
import urllib.error
import urllib.request

URL = "https://api.openai.com/v1/chat/completions"

try:
    import certifi
    CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CONTEXT = ssl.create_default_context()


def model():
    return os.environ.get("OPENAI_MODEL", "gpt-6-luna")


def chat(messages, schema=None):
    """Send the conversation; return the model's message and the usage."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it, then run again.")

    body = {"model": model(), "messages": messages}
    # Parsing against a grammar is classification, not reasoning: no thinking tokens spent on it.
    if model().startswith(("gpt-5", "gpt-6", "o")):
        body["reasoning_effort"] = "none"
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}}

    request = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, context=CONTEXT, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"The model call failed ({e.code}): {e.read().decode()[:300]}") from None
    return data["choices"][0]["message"], data.get("usage", {})
