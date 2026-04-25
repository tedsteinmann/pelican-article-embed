from types import SimpleNamespace

import content_embeds


class DummyContent:
    def __init__(self, html, settings=None):
        self._content = html
        self.settings = settings or {"CONTENT_EMBEDS": {"CARD_PARTIAL": "partials/card_section.html"}}


class DummyTarget:
    def __init__(self, title, url, summary=None, tags=None):
        self.title = title
        self.url = url
        self.summary = summary
        self.tags = tags or []


class FakeTemplate:
    def render(self, context):
        section = context["section"]
        header = f"<header><h2>{section['title']}</h2></header>" if section["title"] else ""
        cards = "".join(
            f"<article><a rel=\"bookmark\" href=\"{card['url']}\">{card['title']}</a>"
            + (f"<p>{card['description']}</p>" if card.get("description") else "")
            + "</article>"
            for card in section["cards"]
        )
        return (
            f"<section class=\"content-section\" id=\"{section['slug']}\">"
            f"{header}<div class=\"content-grid\">{cards}</div></section>"
        )


class FakeEnv:
    def __init__(self, templates):
        self.templates = templates

    def get_template(self, name):
        if name not in self.templates:
            raise content_embeds.TemplateNotFound(name)
        return self.templates[name]


def setup_function(_):
    content_embeds._CONTENT_INDEX.clear()
    content_embeds._JINJA_ENV = None


def _setup_env():
    content_embeds._JINJA_ENV = FakeEnv({"partials/card_section.html": FakeTemplate()})


def test_consecutive_card_paragraphs_grouped_with_heading_title():
    _setup_env()
    content_embeds._CONTENT_INDEX["/blog/eda"] = DummyTarget("EDA", "/blog/eda", "Event driven")
    content_embeds._CONTENT_INDEX["/blog/queues"] = DummyTarget("Queues", "/blog/queues", "Queue intro")

    content = DummyContent(
        "<h2>Architecture Patterns</h2><p><a class='card' href='/blog/eda'>EDA</a></p><p><a class='card' href='/blog/queues'>Queues</a></p>"
    )

    content_embeds._transform_content(content)

    assert "<section class=\"content-section\"" in content._content
    assert "Architecture Patterns" in content._content
    assert content._content.count("rel=\"bookmark\"") == 2


def test_inline_card_link_is_ignored():
    _setup_env()
    content_embeds._CONTENT_INDEX["/blog/eda"] = DummyTarget("EDA", "/blog/eda", "Event driven")

    content = DummyContent("<p>This is <a class='card' href='/blog/eda'>EDA</a> inline.</p>")
    content_embeds._transform_content(content)

    assert "<section class=\"content-section\"" not in content._content
    assert "<p>This is" in content._content
    assert "inline.</p>" in content._content


def test_list_based_cards_grouped():
    _setup_env()
    content_embeds._CONTENT_INDEX["/blog/lakes"] = DummyTarget("Data Lakes", "/blog/lakes")
    content_embeds._CONTENT_INDEX["/blog/warehouse"] = DummyTarget("Warehouse", "/blog/warehouse")

    content = DummyContent("<h3>Data Systems</h3><ul><li><a class='card' href='/blog/lakes'>Lakes</a></li><li><a class='card' href='/blog/warehouse'>Warehouse</a></li></ul>")

    content_embeds._transform_content(content)

    assert "<section class=\"content-section\"" in content._content
    assert "Data Systems" in content._content
    assert "<ul>" not in content._content


def test_unresolved_card_link_degrades_and_warns(caplog):
    _setup_env()
    content = DummyContent("<p><a class='card' href='/blog/missing'>Missing</a></p>")

    with caplog.at_level("WARNING"):
        content_embeds._transform_content(content)

    assert "Could not resolve content link '/blog/missing'." in caplog.text
    assert "<p><a class=\"card\" href=\"/blog/missing\">Missing</a></p>" in content._content


def test_missing_partial_degrades_and_warns(caplog):
    content_embeds._JINJA_ENV = FakeEnv({})
    content_embeds._CONTENT_INDEX["/blog/eda"] = DummyTarget("EDA", "/blog/eda")
    content = DummyContent("<p><a class='card' href='/blog/eda'>EDA</a></p>")

    with caplog.at_level("WARNING"):
        content_embeds._transform_content(content)

    assert "Partial 'partials/card_section.html' not found." in caplog.text
    assert "<p><a class=\"card\" href=\"/blog/eda\">EDA</a></p>" in content._content


def test_build_content_index_uses_generator_items_and_normalizes_url():
    content = DummyTarget("EDA", "/blog/eda/")
    generator = SimpleNamespace(env="env", articles=[content], pages=[], drafts=[])

    content_embeds._build_content_index(generator)

    assert content_embeds._CONTENT_INDEX["/blog/eda"] is content
    assert content_embeds._JINJA_ENV == "env"
