# Pelican Content Embeds (Implicit Card Sections)

Turn simple Markdown links into rich, semantic content cards—grouped automatically into sections—using a lightweight Pelican plugin.

---

## ✨ What This Does

Write normal Markdown like this:

```md
## Architecture Patterns

[Event Driven Architecture](/blog/eda){: .card }
[Message Queues](/blog/queues){: .card }
[Batch Processing](/blog/batch){: .card }
```

And get this at build time:

```html
<section class="content-section">
  <header>
    <h2>Architecture Patterns</h2>
  </header>

  <div class="content-grid">
    <article class="content-card">...</article>
    <article class="content-card">...</article>
    <article class="content-card">...</article>
  </div>
</section>
```

No JavaScript. No custom Markdown syntax. Just clean, semantic HTML.

---

## 🧭 Philosophy

* **Markdown expresses intent** → links with `.card`
* **Plugin infers structure** → groups into sections
* **Theme defines presentation** → via Jinja partials + CSS

---

## 🚀 Features

* ✅ Implicit grouping of consecutive `.card` links
* ✅ Section titles derived from headings
* ✅ Theme-controlled rendering via Jinja partials
* ✅ Fully static output (no JS required)
* ✅ Graceful degradation (links still work without plugin)
* ✅ Works with any CSS framework (including Pico)

---

## 📦 Installation

### 1. Add the plugin

```bash
mkdir -p plugins/content_embeds
```

Copy plugin code into:

```
plugins/content_embeds/
```

---

### 2. Enable in `pelicanconf.py`

```python
PLUGINS = ["content_embeds"]

MARKDOWN = {
    "extensions": ["attr_list"]
}
```

---

### 3. Configure the partial

```python
CONTENT_EMBEDS = {
    "CARD_PARTIAL": "partials/card_section.html"
}
```

---

## 📝 Authoring Guide

### Basic Usage

```md
[Title](/url){: .card }
```

---

### Grouping (Automatic)

Consecutive `.card` links become a section:

```md
## Section Title

[One](/one){: .card }
[Two](/two){: .card }
```

---

### Lists Also Work

```md
## Data Systems

- [Data Lakes](/lakes){: .card }
- [Warehouses](/warehouse){: .card }
```

---

## 🧠 How Grouping Works

Cards are grouped when they are:

* consecutive sibling elements, OR
* inside the same list

A section ends when encountering:

* a non-card element
* a blank line (new paragraph)
* a new heading

---

## 🎨 Theme Integration

You provide the rendering via a Jinja partial.

### Example Partial

```jinja2
<section class="content-card-section" id="{{ section.slug }}">
    {% if section.title %}
    <header>
        <h2>{{ section.title }}</h2>
    </header>
    {% endif %}

    <div class="content-grid">
        {% for card in section.cards %}
        <article class="content-card">
            <h3>
                <a href="{{ card.url }}">{{ card.title }}</a>
            </h3>

            {% if card.description %}
            <p>{{ card.description }}</p>
            {% endif %}
        </article>
        {% endfor %}
    </div>
</section>
```

---

## 🧩 Card Data Model

Each card is populated from the target content:

| Field         | Source                    |
| ------------- | ------------------------- |
| `title`       | `article.title`           |
| `url`         | `article.url`             |
| `description` | `article.summary`         |
| `tags`        | `article.tags` (optional) |

---

## ⚙️ Configuration

```python
CONTENT_EMBEDS = {
    "CARD_PARTIAL": "partials/card_section.html"
}
```

---

## ⚠️ Graceful Degradation

| Scenario         | Behavior                         |
| ---------------- | -------------------------------- |
| Plugin disabled  | Links render normally            |
| Partial missing  | Warning logged, links unchanged  |
| Target not found | Link unchanged                   |
| Missing summary  | Card renders without description |

---

## 🧪 Example Output

### Input

```md
## Architecture

[EDA](/blog/eda){: .card }
[Queues](/blog/queues){: .card }
```

### Output

```html
<section class="content-section">
  <header>
    <h2>Architecture</h2>
  </header>

  <div class="content-grid">
    <article>...</article>
    <article>...</article>
  </div>
</section>
```

---

## 🎯 Design Decisions

### Why not custom Markdown blocks?

Keeps authoring:

* simple
* portable
* readable

---

### Why not JSON-LD rendering?

JSON-LD is for machines, not UI.
Cards are rendered from the same source data instead.

---

### Why not JavaScript?

This plugin is:

* static-first
* fast
* SEO-friendly

---

## 🧠 Mental Model

You are not embedding pages.

You are rendering:

> **structured previews of content using metadata**

---

## 🔮 Future Extensions

* HTMX-powered lazy loading
* External link previews (OpenGraph)
* Related content auto-sections
* Metadata validation (JSON-LD alignment)

---

## 🤝 Contributing

PRs welcome. Keep changes aligned with:

* Markdown-first authoring
* semantic HTML output
* theme-driven presentation

---

## 🏁 Summary

This plugin lets you:

* write simple links
* get structured, styled sections
* keep full control in your theme

---

## 🔑 One-liner

> Turn Markdown links into semantic, grouped content cards—without changing how you write Markdown.
