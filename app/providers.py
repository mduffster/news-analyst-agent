"""Thin wrappers for AI providers with web search."""

import asyncio
from dataclasses import dataclass, field

import anthropic
import openai
from google import genai
from google.genai import types

from app.config import settings


@dataclass
class ProviderResult:
    content: str
    sources: list[dict] = field(default_factory=list)
    model: str = ""
    provider: str = ""


async def call_claude(system_prompt: str, user_message: str) -> ProviderResult:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=16384,
        system=system_prompt,
        tools=[{"name": "web_search", "type": "web_search_20250305"}],
        messages=[{"role": "user", "content": user_message}],
    )

    content_text = ""
    sources = []
    for block in response.content:
        if block.type == "text":
            content_text += block.text
        elif block.type == "web_search_tool_result":
            for result in block.content:
                if hasattr(result, "url"):
                    sources.append(
                        {"url": result.url, "title": getattr(result, "title", "")}
                    )

    # Strip CoT preamble before first heading
    heading_pos = content_text.find("\n#")
    if heading_pos > 0:
        content_text = content_text[heading_pos + 1:]

    return ProviderResult(
        content=content_text,
        sources=sources,
        model=settings.anthropic_model,
        provider="claude",
    )


async def call_gpt(system_prompt: str, user_message: str) -> ProviderResult:
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.responses.create(
        model=settings.openai_model,
        instructions=system_prompt,
        input=user_message,
        tools=[{"type": "web_search"}],
    )

    content_text = response.output_text
    sources = []
    for item in response.output:
        if hasattr(item, "content") and isinstance(item.content, list):
            for part in item.content:
                if hasattr(part, "annotations"):
                    for ann in part.annotations:
                        if hasattr(ann, "url"):
                            sources.append(
                                {"url": ann.url, "title": getattr(ann, "title", "")}
                            )

    return ProviderResult(
        content=content_text,
        sources=sources,
        model=settings.openai_model,
        provider="gpt",
    )


async def call_gemini(system_prompt: str, user_message: str) -> ProviderResult:
    client = genai.Client(api_key=settings.google_api_key)
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    content_text = response.text or ""
    sources = []
    candidate = response.candidates[0] if response.candidates else None
    if candidate and candidate.grounding_metadata:
        for chunk in candidate.grounding_metadata.grounding_chunks or []:
            if chunk.web:
                sources.append(
                    {"url": chunk.web.uri, "title": chunk.web.title or ""}
                )

    return ProviderResult(
        content=content_text,
        sources=sources,
        model=settings.gemini_model,
        provider="gemini",
    )


async def call_all(
    system_prompt: str, user_message: str
) -> dict[str, ProviderResult]:
    """Call all configured providers in parallel."""
    tasks = {}
    if settings.anthropic_api_key:
        tasks["claude"] = call_claude(system_prompt, user_message)
    if settings.openai_api_key:
        tasks["gpt"] = call_gpt(system_prompt, user_message)
    if settings.google_api_key:
        tasks["gemini"] = call_gemini(system_prompt, user_message)

    if not tasks:
        raise ValueError("No AI providers configured — check API keys in .env")

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    output = {}
    for name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            print(f"  [ERROR] {name}: {result}")
        else:
            output[name] = result
    return output


async def call_synthesis(system_prompt: str, user_message: str) -> ProviderResult:
    """Call the configured synthesis provider."""
    provider = settings.synthesis_provider
    if provider == "anthropic":
        return await call_claude(system_prompt, user_message)
    elif provider == "openai":
        return await call_gpt(system_prompt, user_message)
    elif provider == "gemini":
        return await call_gemini(system_prompt, user_message)
    else:
        raise ValueError(f"Unknown synthesis provider: {provider}")
