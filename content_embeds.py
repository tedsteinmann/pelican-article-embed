"""Pelican plugin for implicit content card embeds."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

try:
    from jinja2 import Environment, TemplateNotFound
except ImportError:  # pragma: no cover - fallback for lightweight test environments
    Environment = object  # type: ignore[misc,assignment]

    class TemplateNotFound(Exception):
        pass

try:
    from pelican import signals
except ImportError:  # pragma: no cover - fallback for lightweight test environments
    class _NoopSignal:
        def connect(self, *_args, **_kwargs):
            return None

    class _NoopSignals:
        article_generator_finalized = _NoopSignal()
        page_generator_finalized = _NoopSignal()
        content_object_init = _NoopSignal()

    signals = _NoopSignals()

LOGGER = logging.getLogger(__name__)

DEFAULT_PARTIAL = "partials/card_section.html"

_CONTENT_INDEX: Dict[str, object] = {}
_JINJA_ENV: Optional[Environment] = None


@dataclass
class HeadingContext:
    level: int
    text: str


def _warn(message: str) -> None:
    LOGGER.warning("[content_embeds] WARNING: %s", message)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "content-cards"


def _normalize_href(href: Optional[str]) -> Optional[str]:
    if not href:
        return None

    parsed = urlparse(href)
    path = parsed.path or ""
    if not path:
        return None

    if not path.startswith("/"):
        path = f"/{path}"

    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    return path


def _iter_generator_content(generator: object) -> Sequence[object]:
    attrs = (
        "articles",
        "drafts",
        "hidden_articles",
        "hidden_pages",
        "pages",
        "translations",
    )

    collected: List[object] = []
    for attr in attrs:
        for item in getattr(generator, attr, []) or []:
            collected.append(item)
    return collected


def _build_content_index(generator: object) -> None:
    global _JINJA_ENV

    if hasattr(generator, "env"):
        _JINJA_ENV = generator.env

    for content in _iter_generator_content(generator):
        normalized = _normalize_href(getattr(content, "url", None))
        if normalized:
            _CONTENT_INDEX[normalized] = content


def _is_heading(element: ET.Element) -> bool:
    return bool(re.fullmatch(r"h[1-6]", element.tag or ""))


def _element_text(element: ET.Element) -> str:
    return "".join(element.itertext()).strip()


def _anchor_is_card(anchor: ET.Element) -> bool:
    class_name = anchor.attrib.get("class", "")
    classes = {chunk.strip() for chunk in class_name.split() if chunk.strip()}
    return "card" in classes


def _single_card_anchor(element: ET.Element) -> Optional[ET.Element]:
    if element.tag not in {"p", "li"}:
        return None

    if (element.text or "").strip():
        return None

    children = list(element)
    if len(children) != 1:
        return None

    anchor = children[0]
    if anchor.tag != "a" or not _anchor_is_card(anchor):
        return None

    if (anchor.tail or "").strip():
        return None

    return anchor


def _is_card_list(element: ET.Element) -> bool:
    if element.tag not in {"ul", "ol"}:
        return False

    items = list(element)
    if not items:
        return False

    for item in items:
        if item.tag != "li" or _single_card_anchor(item) is None:
            return False

    return True


def _resolve_card(anchor: ET.Element) -> Optional[Dict[str, object]]:
    href = _normalize_href(anchor.attrib.get("href"))
    target = _CONTENT_INDEX.get(href or "")
    if not target:
        if href:
            _warn(f"Could not resolve content link '{href}'.")
        return None

    return {
        "title": getattr(target, "title", _element_text(anchor)),
        "url": getattr(target, "url", anchor.attrib.get("href", "#")),
        "description": getattr(target, "summary", None),
        "tags": [getattr(tag, "name", str(tag)) for tag in getattr(target, "tags", []) or []],
        "eyebrow": None,
        "meta": None,
        "cta_label": "More",
    }


def _render_section(settings: dict, heading: Optional[HeadingContext], cards: List[Dict[str, object]]) -> Optional[str]:
    global _JINJA_ENV

    if _JINJA_ENV is None:
        return None

    config = settings.get("CONTENT_EMBEDS", {}) or {}
    template_name = config.get("CARD_PARTIAL", DEFAULT_PARTIAL)

    try:
        template = _JINJA_ENV.get_template(template_name)
    except TemplateNotFound:
        _warn(f"Partial '{template_name}' not found.")
        return None

    section_title = heading.text if heading else None
    seed = section_title or cards[0]["title"]

    context = {
        "section": {
            "title": section_title,
            "description": None,
            "anchor": None,
            "slug": _slugify(str(seed)),
            "cards": cards,
        }
    }
    return template.render(context)


def _transform_content(content: object) -> None:
    html = getattr(content, "_content", None)
    if not html:
        return

    try:
        root = ET.fromstring(f"<div>{html}</div>")
    except ET.ParseError:
        return

    children = list(root)
    rendered_chunks: List[str] = []
    heading: Optional[HeadingContext] = None

    idx = 0
    while idx < len(children):
        node = children[idx]

        if _is_heading(node):
            heading = HeadingContext(level=int(node.tag[1]), text=_element_text(node))
            rendered_chunks.append(ET.tostring(node, encoding="unicode", method="html"))
            idx += 1
            continue

        if _is_card_list(node):
            anchors = [_single_card_anchor(item) for item in list(node)]
            cards = []
            unresolved = False
            for anchor in anchors:
                resolved = _resolve_card(anchor) if anchor is not None else None
                if resolved is None:
                    unresolved = True
                    break
                cards.append(resolved)

            if unresolved:
                rendered_chunks.append(ET.tostring(node, encoding="unicode", method="html"))
                idx += 1
                continue

            section_html = _render_section(content.settings, heading, cards)
            if section_html is None:
                rendered_chunks.append(ET.tostring(node, encoding="unicode", method="html"))
            else:
                rendered_chunks.append(section_html)
            idx += 1
            continue

        first_anchor = _single_card_anchor(node)
        if first_anchor is None:
            rendered_chunks.append(ET.tostring(node, encoding="unicode", method="html"))
            idx += 1
            continue

        block_nodes: List[ET.Element] = []
        block_cards: List[Dict[str, object]] = []
        unresolved = False

        while idx < len(children):
            sibling = children[idx]
            anchor = _single_card_anchor(sibling)
            if anchor is None:
                break

            resolved = _resolve_card(anchor)
            if resolved is None:
                unresolved = True
                break

            block_nodes.append(sibling)
            block_cards.append(resolved)
            idx += 1

        if not block_nodes:
            rendered_chunks.append(ET.tostring(node, encoding="unicode", method="html"))
            idx += 1
            continue

        if unresolved:
            for block in block_nodes:
                rendered_chunks.append(ET.tostring(block, encoding="unicode", method="html"))
            continue

        section_html = _render_section(content.settings, heading, block_cards)
        if section_html is None:
            for block in block_nodes:
                rendered_chunks.append(ET.tostring(block, encoding="unicode", method="html"))
        else:
            rendered_chunks.append(section_html)

    content._content = "\n".join(rendered_chunks)


def register() -> None:
    signals.article_generator_finalized.connect(_build_content_index)
    signals.page_generator_finalized.connect(_build_content_index)
    signals.content_object_init.connect(_transform_content)
