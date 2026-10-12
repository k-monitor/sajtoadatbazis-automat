from os import environ
from time import sleep
from typing import Optional
import json
import logging
import re
import traceback
import requests
from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse
from auto_kmdb import chatgpt, db
from auto_kmdb.processors import Processor
from auto_kmdb.processors.description_prompts import (
    RELATED_TYPES,
    build_prompt_text,
    system_instruction,
)

# "gemini", "openai" for any OpenAI compatible chat completions API (OpenRouter, Ollama, vLLM...), or
# "chatgpt" for the ChatGPT plan of the account connected on the descriptions page.
DESCRIPTION_PROVIDER = environ.get("DESCRIPTION_PROVIDER", "gemini")
DESCRIPTION_GEMINI_MODEL = environ.get("DESCRIPTION_GEMINI_MODEL", "gemini-3.5-flash-lite")
DESCRIPTION_OPENAI_BASE_URL = environ.get("DESCRIPTION_OPENAI_BASE_URL", "https://api.openai.com/v1")
DESCRIPTION_OPENAI_MODEL = environ.get("DESCRIPTION_OPENAI_MODEL", "")
# JSON object merged into the request, e.g. to turn on the web search of the provider.
DESCRIPTION_OPENAI_EXTRA_BODY = environ.get("DESCRIPTION_OPENAI_EXTRA_BODY", "")
# Gemini always gets Google Search, OpenAI compatible models only if they can search the web.
DESCRIPTION_OPENAI_WEB_SEARCH = environ.get("DESCRIPTION_OPENAI_WEB_SEARCH", "false").lower() == "true"
# Empty for the default model of the connected account.
DESCRIPTION_CHATGPT_MODEL = environ.get("DESCRIPTION_CHATGPT_MODEL", "")
# The web search of the plan depends on the model and the account.
DESCRIPTION_CHATGPT_WEB_SEARCH = environ.get("DESCRIPTION_CHATGPT_WEB_SEARCH", "true").lower() == "true"
# Only the latest articles are given, the model searches the web for the rest.
DESCRIPTION_MAX_ARTICLES = int(environ.get("DESCRIPTION_MAX_ARTICLES", "10"))


def description_model() -> str:
    if DESCRIPTION_PROVIDER == "chatgpt":
        return DESCRIPTION_CHATGPT_MODEL or chatgpt.default_model()
    return DESCRIPTION_OPENAI_MODEL if DESCRIPTION_PROVIDER == "openai" else DESCRIPTION_GEMINI_MODEL


def web_search_enabled() -> bool:
    if DESCRIPTION_PROVIDER == "chatgpt":
        return DESCRIPTION_CHATGPT_WEB_SEARCH
    return DESCRIPTION_OPENAI_WEB_SEARCH if DESCRIPTION_PROVIDER == "openai" else True


def build_prompt(entity_type: str, entity_id: int) -> dict:
    """
    Collects what the KMDB knows about the entity and builds the prompt from it, without calling
    the model, so it can also be previewed on the UI.

    Returns:
        Dict with the 'entity' (see db.get_description_entity), the 'system_instruction' and
        'prompt' texts, whether the model can use 'web_search' and the articles given as 'sources'.
    """
    entity = db.get_description_entity(entity_type, entity_id)
    if entity is None:
        raise ValueError(f"Nem található {entity_type} ezzel az azonosítóval: {entity_id}")

    if entity_type == "newspaper":
        articles = db.get_articles_mentioning(entity["name"], DESCRIPTION_MAX_ARTICLES)
    else:
        articles = db.get_description_articles(entity_type, entity_id, DESCRIPTION_MAX_ARTICLES)
    related = {
        related_type: db.get_description_related(entity_type, entity_id, related_type)
        for related_type in RELATED_TYPES[entity_type]
    }
    prompt = build_prompt_text(
        entity_type,
        entity["name"],
        entity["url"],
        entity["description"],
        articles,
        len(articles) >= DESCRIPTION_MAX_ARTICLES,
        related,
        web_search_enabled(),
    )
    return {
        "entity": entity,
        "system_instruction": system_instruction(web_search_enabled()),
        "prompt": prompt,
        "web_search": web_search_enabled(),
        "sources": [
            {"kind": "kmdb", **{k: a[k] for k in ("url", "title", "date", "newspaper")}}
            for a in articles
        ],
    }


def resolve_search_url(uri: str) -> str:
    """The grounding chunks link to a Google redirect that expires, so its target is kept."""
    try:
        response = requests.get(uri, allow_redirects=False, timeout=10, stream=True)
        response.close()
        return response.headers.get("Location", uri)
    except requests.RequestException:
        return uri


def _is_citable(url: Optional[str]) -> bool:
    return bool(url) and not db.is_kmdb_url(url)


def cite_search_results(response: GenerateContentResponse) -> tuple[str, list[dict]]:
    """
    The model rarely writes the URLs of the Google Search results it used, so they are cited as
    [url] after the text segments that the grounding metadata says they support.

    Returns:
        The response text with the citations, and the search results as sources.
    """
    text = response.text
    metadata = response.candidates[0].grounding_metadata if response.candidates else None
    logging.info(
        f"Grounding metadata: {len(metadata.grounding_chunks or [])} chunks, "
        f"{len(metadata.grounding_supports or [])} supports, queries: {metadata.web_search_queries}"
        if metadata else "No grounding metadata"
    )
    if not metadata or not metadata.grounding_chunks:
        return text.strip(), []

    chunk_urls = [
        resolve_search_url(chunk.web.uri) if chunk.web and chunk.web.uri else None
        for chunk in metadata.grounding_chunks
    ]
    sources: list[dict] = []
    for chunk, url in zip(metadata.grounding_chunks, chunk_urls):
        if url and all(source["url"] != url for source in sources):
            sources.append({"kind": "search", "url": url, "title": chunk.web.title or ""})

    # The segments are located by their text, as their indices are bytes of the UTF-8 text.
    citations: dict[int, list[str]] = {}
    for support in metadata.grounding_supports or []:
        segment = support.segment
        if not segment or not segment.text or segment.text not in text:
            continue
        end = text.index(segment.text) + len(segment.text)
        for index in support.grounding_chunk_indices or []:
            url = chunk_urls[index] if index < len(chunk_urls) else None
            already_cited = url in segment.text or url in text[end:end + len(url) + 10]
            if _is_citable(url) and not already_cited and url not in citations.get(end, []):
                citations.setdefault(end, []).append(url)
    for end in sorted(citations, reverse=True):
        text = text[:end] + "".join(f" [{url}]" for url in citations[end]) + text[end:]
    return text.strip(), sources


def generate_gemini_description(
    system_instruction: str, prompt: str
) -> tuple[str, dict, list[dict]]:
    if not environ.get("GEMINI_API_KEY"):
        raise ValueError("A GEMINI_API_KEY nincs beállítva a backend környezetében (pl. webapp/data/.env).")
    print(environ.get("GEMINI_API_KEY"))
    client = genai.Client(api_key=environ.get("GEMINI_API_KEY"))
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    response: GenerateContentResponse = client.models.generate_content(
        model=DESCRIPTION_GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    if not response.text:
        reason = (
            response.candidates[0].finish_reason
            if response.candidates
            else response.prompt_feedback
        )
        raise ValueError(f"Üres válasz a Gemini-től: {reason}")

    token_counts = {
        "prompt": response.usage_metadata.prompt_token_count,
        "response": response.usage_metadata.candidates_token_count,
        "thinking": response.usage_metadata.thoughts_token_count,
    }
    text, found_sources = cite_search_results(response)
    return text, token_counts, found_sources


# Reasoning models served locally (e.g. by Ollama or vLLM) may put their thinking in the content.
_THINKING = re.compile(r"^\s*<think>.*?</think>", re.DOTALL)


def openai_search_sources(data: dict) -> list[dict]:
    """
    The web pages that the providers with web search report: OpenAI and OpenRouter as url_citation
    annotations, Perplexity as citations and search_results.
    """
    message = data["choices"][0]["message"]
    found = [
        (a["url_citation"].get("url"), a["url_citation"].get("title"))
        for a in message.get("annotations") or []
        if a.get("type") == "url_citation" and a.get("url_citation")
    ]
    found += [(r.get("url"), r.get("title")) for r in data.get("search_results") or []]
    found += [(url, "") for url in data.get("citations") or [] if isinstance(url, str)]
    sources: list[dict] = []
    for url, title in found:
        if url and all(source["url"] != url for source in sources):
            sources.append({"kind": "search", "url": url, "title": title or ""})
    return sources


def generate_openai_description(
    system_instruction: str, prompt: str
) -> tuple[str, dict, list[dict]]:
    if not DESCRIPTION_OPENAI_MODEL:
        raise ValueError("A DESCRIPTION_OPENAI_MODEL nincs beállítva a backend környezetében.")
    api_key = environ.get("DESCRIPTION_OPENAI_API_KEY")
    response = requests.post(
        f"{DESCRIPTION_OPENAI_BASE_URL.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        json={
            "model": DESCRIPTION_OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            **json.loads(DESCRIPTION_OPENAI_EXTRA_BODY or "{}"),
        },
        timeout=600,
    )
    if not response.ok:
        raise ValueError(f"{response.status_code} hiba az OpenAI kompatibilis API-tól: {response.text[:1000]}")
    data = response.json()
    if not data.get("choices"):
        raise ValueError(f"Válasz nélküli eredmény az OpenAI kompatibilis API-tól: {str(data)[:1000]}")

    choice = data["choices"][0]
    text = _THINKING.sub("", choice["message"].get("content") or "").strip()
    if not text:
        raise ValueError(f"Üres válasz az OpenAI kompatibilis API-tól: {choice.get('finish_reason')}")
    usage = data.get("usage") or {}
    token_counts = {
        "prompt": usage.get("prompt_tokens"),
        "response": usage.get("completion_tokens"),
        "thinking": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
    }
    return text, token_counts, openai_search_sources(data)


def generate_chatgpt_description(
    system_instruction: str, prompt: str
) -> tuple[str, dict, list[dict]]:
    response = chatgpt.create_response(
        {
            "model": description_model(),
            "instructions": system_instruction,
            "input": [{"role": "user", "content": prompt}],
            **({"tools": [{"type": "web_search"}]} if DESCRIPTION_CHATGPT_WEB_SEARCH else {}),
        }
    )
    texts: list[str] = []
    sources: list[dict] = []
    for item in response.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") != "output_text":
                continue
            texts.append(part.get("text") or "")
            for annotation in part.get("annotations") or []:
                url = annotation.get("url")
                if annotation.get("type") == "url_citation" and url and all(s["url"] != url for s in sources):
                    sources.append({"kind": "search", "url": url, "title": annotation.get("title") or ""})
    text = "".join(texts).strip()
    if not text:
        raise ValueError(f"Üres válasz a ChatGPT-től: {response.get('status')}")

    usage = response.get("usage") or {}
    token_counts = {
        "prompt": usage.get("input_tokens"),
        "response": usage.get("output_tokens"),
        "thinking": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
    }
    return text, token_counts, sources


def generate_description(system_instruction: str, prompt: str) -> tuple[str, dict, list[dict]]:
    """
    Returns:
        The generated markdown description with the sources cited, the token counts and the web
        search results used.
    """
    if DESCRIPTION_PROVIDER == "gemini":
        return generate_gemini_description(system_instruction, prompt)
    if DESCRIPTION_PROVIDER == "openai":
        return generate_openai_description(system_instruction, prompt)
    if DESCRIPTION_PROVIDER == "chatgpt":
        return generate_chatgpt_description(system_instruction, prompt)
    raise ValueError(
        f"Ismeretlen DESCRIPTION_PROVIDER: {DESCRIPTION_PROVIDER} (gemini, openai vagy chatgpt lehet)"
    )


class DescriptionProcessor(Processor):
    """
    Generates the description suggestions of the entities queued on the descriptions page. Failed
    requests are not retried automatically, they can be queued again from the UI. While the ChatGPT
    plan can not be used (not connected, usage limit), the requests wait in the queue.
    """

    def process_next(self):
        request = db.get_next_description_request()
        if request is None:
            sleep(30)
            return

        try:
            built = build_prompt(request["entity_type"], request["entity_id"])
            model = description_model()
            suggestion, token_counts, found_sources = generate_description(
                built["system_instruction"], built["prompt"]
            )
            db.save_description_suggestion(
                request["id"],
                suggestion,
                built["sources"] + found_sources,
                f"{built['system_instruction']}\n\n---\n\n{built['prompt']}",
                model,
                token_counts,
            )
            logging.info(
                f"Generated description for {request['entity_type']} {request['entity_id']}, "
                f"token counts: {token_counts}"
            )
        except chatgpt.ChatGPTUnavailable as e:
            logging.warning(f"Description generation paused for {e.retry_after}s: {e}")
            sleep(e.retry_after)
        except Exception as e:
            logging.error(
                f"Error generating description {request['id']}: {e}\n{traceback.format_exc()}"
            )
            db.save_description_error(request["id"], str(e))
