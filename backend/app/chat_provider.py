"""OpenAI-compatible chat completions for hosted OpenRouter and NVIDIA NIM."""
import json

import httpx

from . import db, provider_keys
from .cloud import CloudRefusal, CloudTasks


class ChatProvider(CloudTasks):
    ENDPOINTS = {"openrouter": "https://openrouter.ai/api/v1/chat/completions",
                 "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions"}

    def __init__(self, name, client=None):
        super().__init__()
        self.name = name
        self.endpoint = self.ENDPOINTS[name]
        self.client = client or httpx.Client(timeout=90)

    def model(self):
        with db.connect() as c:
            return c.execute("SELECT * FROM settings").fetchone()[f"{self.name}_model"]

    def _request(self, model, kind, content, schema, max_tokens):
        # Ask for JSON in the prompt so models without a structured-output API can participate.
        instructions = "Return a single JSON object matching this schema:\n" + json.dumps(schema.model_json_schema())
        parts = [p for p in content if p["type"] == "text"]
        for p in content:
            if p["type"] == "image":
                url = "data:image/png;base64," + p["source"]["data"]
                parts.append({"type": "image_url", "image_url": {"url": url}})
        user_content = parts if len(parts) > 1 else parts[0]["text"]
        payload = {"model": model, "messages": [{"role": "system", "content": instructions},
                   {"role": "user", "content": user_content}]}
        attempted = set()
        while True:
            key = provider_keys.next_key(self.name, attempted)
            attempted.add(key)
            try:
                response = self.client.post(self.endpoint, headers={"Authorization": f"Bearer {key}"}, json=payload)
            except httpx.RequestError:
                raise CloudRefusal(f"Could not reach {self.name}. Check the server connection.") from None
            if response.status_code != 429:
                break
            provider_keys.cool_down(self.name, key, response.headers.get("Retry-After"))
        if not response.is_success:
            raise CloudRefusal(f"{self.name} returned HTTP {response.status_code} for {kind}. "
                               "Check the model ID, input support, API key and available credits.")
        try:
            choice = response.json()["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise CloudRefusal(f"{self.name} did not complete {kind}. Check the selected model.")
            result = choice["message"]["content"].strip()
            if result.startswith("```") and result.endswith("```"):
                result = result.removeprefix("```").removeprefix("json").removesuffix("```").strip()
            return schema.model_validate_json(result)
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            raise CloudRefusal(f"{self.name} returned an invalid {kind} result. Check the selected model.") from None
