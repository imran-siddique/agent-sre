"""
Helicone integration — add Helicone tracking headers to LLM requests.

Usage:
    from agent_sre.integrations.helicone import HeliconeHeaders
    headers = HeliconeHeaders(api_key="sk-...", agent_id="my-agent")
    headers_dict = headers.get_headers(session_name="task-1")
"""
from agent_sre.integrations.helicone.headers import HeliconeHeaders, HeliconeLogger

__all__ = ["HeliconeHeaders", "HeliconeLogger"]
