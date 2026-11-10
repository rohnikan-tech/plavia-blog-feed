"""The gate for this repository. Stdlib only, Python 3.9+.

  python tools/validate.py              check the repository; exit 1 and one line per violation
  python tools/validate.py --selftest   feed built-in bad fixtures to the checks; each must be rejected
"""
import html
import importlib.util
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("build_feed", os.path.join(HERE, "build_feed.py"))
build_feed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_feed)

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CATEGORIES = {"ai": ("هوش مصنوعی", "AI"), "tech": ("فناوری و گجت", "Technology"), "product": ("محصول", "Product")}
POST_FILES = {"post.html", "meta.json", "cover.svg", "cover.png", "post.en.html"}
REQUIRED_FILES = {"post.html", "meta.json", "cover.svg", "cover.png"}
TEXT_KEYS = ("title", "excerpt", "category_fa", "category_en", "seo_title", "meta_description", "cover_alt")
REQUIRED = {"slug": str, "lang": str, "stream": str, "title": str, "excerpt": str, "category": str,
            "category_fa": str, "category_en": str, "tags": list, "seo_title": str, "meta_description": str,
            "reading_minutes": int, "publish_at": str, "revision": int, "cover_alt": str, "sources": list,
            "focus_queries": list}
OPTIONAL = {"release_ref": str, "title_en": str, "excerpt_en": str}
SOURCE_KEYS = {"title", "url", "date_read"}
SOURCE_OPTIONAL = {"date_published"}
HTML_TAGS = {"h2", "h3", "p", "ul", "ol", "li", "a", "strong", "em", "blockquote", "table", "thead", "tbody",
             "tr", "th", "td", "code", "br"}
SVG_NS = "{http://www.w3.org/2000/svg}"
SVG_TAGS = {"svg", "g", "defs", "linearGradient", "radialGradient", "stop", "clipPath", "rect", "circle",
            "ellipse", "line", "polyline", "polygon", "path"}
PLAVIA_HOSTS = {"plavia.ir", "www.plavia.ir"}
WORDS = {"editorial": (800, 1500), "product": (150, 1500)}
BLOG_LINK_RE = re.compile(r"^/blog/([^/]+)/$")
MAX_POST_LINKS = 2


# ---------------------------------------------------------------- post.html
class _PostParser(HTMLParser):
    def __init__(self, links, posts, when):
        super().__init__(convert_charrefs=True)
        self.links, self.errors, self.text, self.plavia_links = links, [], [], 0
        self.posts, self.when, self.post_links = posts, when, 0

    def _tag(self, tag, attrs):
        if tag not in HTML_TAGS:
            self.errors.append("tag not allowed: <%s>" % tag)
        for name, value in attrs:
            if not (tag == "a" and name == "href"):
                self.errors.append("attribute not allowed: %s on <%s>" % (name, tag))
        if tag == "a":
            hrefs = [v for n, v in attrs if n == "href"]
            if not hrefs:
                self.errors.append("<a> without href")
            for href in hrefs:
                self._href(href or "")

    def _href(self, href):
        if href in self.links:
            self.plavia_links += 1
            return
        blog = BLOG_LINK_RE.match(href)
        if blog:
            other = self.posts.get(blog.group(1))
            if other is None:
                self.errors.append("links to a post that does not exist in this repository: %s" % href[:80])
            elif self.when is None or not other < self.when:
                self.errors.append("links to a post that is not dated earlier than this one: %s" % href[:80])
            else:
                self.post_links += 1
            return
        parts = urlsplit(href)
        if href.startswith("https://") and parts.netloc and not re.search(r"[\s<>\"'\\]", href):
            if parts.hostname in PLAVIA_HOSTS:
                self.plavia_links += 1
            return
        self.errors.append("href not allowed (https:// or a path in site-links.txt only): %s" % href[:80])

    def handle_starttag(self, tag, attrs):
        self._tag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._tag(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in HTML_TAGS:
            self.errors.append("tag not allowed: </%s>" % tag)

    def handle_data(self, data):
        self.text.append(data)

    def handle_comment(self, data):
        self.errors.append("HTML comment not allowed")

    def handle_decl(self, decl):
        self.errors.append("declaration not allowed: <!%s>" % decl[:40])

    def unknown_decl(self, data):
        self.errors.append("declaration not allowed: <![%s" % data[:40])

    def handle_pi(self, data):
        self.errors.append("processing instruction not allowed")


def check_post_html(raw, links, stream=None, posts=None, when=None):
    """Return (errors, word count). stream=None skips the word-count rule (translations).
    posts = {slug: publish_at datetime} of every post; when = this post's publish_at (for /blog/<slug>/ links)."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["not UTF-8"], 0
    errors = []
    if "]]>" in text:
        errors.append("']]>' not allowed")
    if "<script" in html.unescape(text).lower():
        errors.append("text that decodes to '<script' not allowed")
    p = _PostParser(links, posts or {}, when)
    p.feed(text)
    p.close()
    errors += p.errors
    if p.plavia_links > 1:
        errors.append("at most one link to a plavia.ir path (found %d)" % p.plavia_links)
    if p.post_links > MAX_POST_LINKS:
        errors.append("at most %d links to earlier posts (found %d)" % (MAX_POST_LINKS, p.post_links))
    words = len(" ".join(p.text).split())
    if stream in WORDS:
        lo, hi = WORDS[stream]
        if not lo <= words <= hi:
            errors.append("word count %d outside %d-%d for %s" % (words, lo, hi, stream))
    return errors, words


# ---------------------------------------------------------------- cover.svg / cover.png
def check_svg(raw):
    errors = []
    if len(raw) >= 25 * 1024:
        errors.append("cover.svg is %d bytes (limit: under 25 KB)" % len(raw))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return errors + ["cover.svg not UTF-8"]
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        return errors + ["cover.svg: DOCTYPE / entity declarations not allowed"]
    if re.search(r"<\?(?!xml\s)", text) or text.count("<?") > 1:
        errors.append("cover.svg: processing instruction not allowed")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return errors + ["cover.svg: not well-formed XML (%s)" % e]
    if root.tag != SVG_NS + "svg":
        errors.append("cover.svg: root must be <svg> in the SVG namespace")
    if root.get("viewBox") != "0 0 1200 630":
        errors.append('cover.svg: viewBox must be "0 0 1200 630"')
    for el in root.iter():
        tag = el.tag
        local = tag[len(SVG_NS):] if isinstance(tag, str) and tag.startswith(SVG_NS) else None
        if local not in SVG_TAGS:
            errors.append("cover.svg: element not allowed: %s" % tag)
        if (el.text or "").strip() or (el.tail or "").strip():
            errors.append("cover.svg: text content not allowed in <%s>" % local)
        for name, value in el.attrib.items():
            short = name.rsplit("}", 1)[-1].lower()
            if short.startswith("on") or short in ("href", "style"):
                errors.append("cover.svg: attribute not allowed: %s on <%s>" % (name, local))
            rest = re.sub(r"url\(#[A-Za-z_][\w.-]*\)", "", value)
            if "url(" in rest.lower().replace(" ", ""):
                errors.append("cover.svg: url() must be url(#local-id): %s" % value[:60])
    return errors


def check_png(raw):
    errors = []
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        return ["cover.png: not a PNG"]
    w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if (w, h) != (1200, 630):
        errors.append("cover.png: %dx%d (must be 1200x630)" % (w, h))
    if len(raw) >= 400 * 1024:
        errors.append("cover.png: %d bytes (limit: under 400 KB)" % len(raw))
    return errors


# ---------------------------------------------------------------- meta.json
def check_meta(m, folder, files):
    errors = []
    if not isinstance(m, dict):
        return ["meta.json: not an object"]
    for key in m:
        if key not in REQUIRED and key not in OPTIONAL:
            errors.append("meta.json: unknown key %s" % key)
    for key, typ in list(REQUIRED.items()) + list(OPTIONAL.items()):
        if key not in m:
            if key in REQUIRED:
                errors.append("meta.json: missing %s" % key)
            continue
        v = m[key]
        if not isinstance(v, typ) or isinstance(v, bool) or (typ is str and not v.strip()):
            errors.append("meta.json: %s must be a non-empty %s" % (key, typ.__name__))
    if errors:
        return errors
    for key in TEXT_KEYS + ("title_en", "excerpt_en"):
        if key in m and re.search(r"[<>\x00-\x08\x0b\x0c\x0e-\x1f]", m[key]):
            errors.append("meta.json: %s contains '<', '>' or a control character" % key)
    for key in ("excerpt", "meta_description", "excerpt_en"):
        if key in m and len(m[key]) > 160:
            errors.append("meta.json: %s is %d characters (max 160)" % (key, len(m[key])))
    if not 70 <= len(m["meta_description"]) <= 160:
        errors.append("meta.json: meta_description is %d characters (must be 70-160)" % len(m["meta_description"]))
    fq = m["focus_queries"]
    if not 1 <= len(fq) <= 3:
        errors.append("meta.json: focus_queries must hold 1-3 phrases (found %d)" % len(fq))
    if not all(isinstance(q, str) and 2 <= len(q.strip()) <= 60 and q == q.strip() and not re.search(r"[<>|]", q)
               for q in fq):
        errors.append("meta.json: each focus query must be a 2-60 character phrase without '<' '>' '|'")
    elif len(set(fq)) != len(fq):
        errors.append("meta.json: duplicate focus query")
    for key, limit in (("title", 120), ("seo_title", 65), ("cover_alt", 250)):
        if len(m[key]) > limit:
            errors.append("meta.json: %s is %d characters (max %d)" % (key, len(m[key]), limit))
    slug = m["slug"]
    if not SLUG_RE.match(slug) or len(slug) > 80:
        errors.append("meta.json: bad slug %r (lowercase a-z 0-9 words joined by '-', max 80)" % slug)
    if m["lang"] != "fa":
        errors.append('meta.json: lang must be "fa"')
    if m["stream"] not in WORDS:
        errors.append('meta.json: stream must be "editorial" or "product"')
    cat = CATEGORIES.get(m["category"])
    if cat is None:
        errors.append("meta.json: category %r not in %s" % (m["category"], sorted(CATEGORIES)))
    elif (m["category_fa"], m["category_en"]) != cat:
        errors.append("meta.json: category %s must be named %s / %s" % (m["category"], cat[0], cat[1]))
    if (m["stream"] == "product") != (m["category"] == "product"):
        errors.append("meta.json: the product stream and the product category go together")
    tags = m["tags"]
    if not 1 <= len(tags) <= 6:
        errors.append("meta.json: tags must hold 1-6 entries")
    if len(set(map(str, tags))) != len(tags):
        errors.append("meta.json: duplicate tag")
    for t in tags:
        if not isinstance(t, str) or not t.strip() or len(t) > 40 or re.search(r"[,<>]", t):
            errors.append("meta.json: bad tag %r (non-empty, max 40, no ',' '<' '>')" % (t,))
    if m["reading_minutes"] < 1 or m["revision"] < 1:
        errors.append("meta.json: reading_minutes and revision must be >= 1")
    when = None
    if TIME_RE.match(m["publish_at"]):
        try:
            when = datetime.fromisoformat(m["publish_at"])
        except ValueError:
            pass
    if when is None:
        errors.append("meta.json: publish_at must be ISO 8601 with offset, e.g. 2026-11-14T08:00:00+03:30")
    parts = folder.split("/")
    if when and parts[1:3] != ["%04d" % when.year, "%02d" % when.month]:
        errors.append("path: %s does not match publish_at %s (YYYY/MM)" % (folder, m["publish_at"]))
    if parts[3] != slug:
        errors.append("path: folder %s does not match slug %s" % (parts[3], slug))
    https_sources = 0
    for s in m["sources"]:
        if not isinstance(s, dict) or not SOURCE_KEYS <= set(s) or not set(s) <= SOURCE_KEYS | SOURCE_OPTIONAL \
                or not all(isinstance(v, str) and v.strip() for v in s.values()):
            errors.append("meta.json: each source needs title, url, date_read (strings), optional date_published")
            continue
        if not DATE_RE.match(s["date_read"]):
            errors.append("meta.json: source date_read must be YYYY-MM-DD")
        u = urlsplit(s["url"])
        if s["url"].startswith("https://") and u.netloc and not re.search(r"\s", s["url"]):
            https_sources += 1
        else:
            errors.append("meta.json: source url must be https://: %s" % s["url"][:80])
    if m["stream"] == "editorial":
        if https_sources < 2:
            errors.append("meta.json: editorial posts need at least 2 sources with https URLs (found %d)" % https_sources)
        if "release_ref" in m:
            errors.append("meta.json: release_ref is for product posts only")
    if m["stream"] == "product":
        ref = m.get("release_ref", "")
        if not ref.startswith("releases/") or ".." in ref or ref == "releases/README.md" or ref not in files:
            errors.append("meta.json: product posts need release_ref naming an existing file under releases/")
    return errors


# ---------------------------------------------------------------- whole tree
def validate(files, check_feed=True):
    errors = []
    links = set()
    if "site-links.txt" not in files:
        errors.append("site-links.txt missing")
    else:
        for line in files["site-links.txt"].decode("utf-8").splitlines():
            if line.strip():
                if not re.match(r"^/[A-Za-z0-9/_.-]*$", line):
                    errors.append("site-links.txt: bad path %r" % line)
                links.add(line)
    folders = {}
    for rel in sorted(files):
        if not rel.startswith("posts/"):
            continue
        parts = rel.split("/")
        if len(parts) != 5 or not re.match(r"^\d{4}$", parts[1]) or not re.match(r"^(0[1-9]|1[0-2])$", parts[2]) \
                or parts[4] not in POST_FILES:
            errors.append("unexpected file %s (posts/YYYY/MM/<slug>/{%s})" % (rel, ",".join(sorted(POST_FILES))))
            continue
        folders.setdefault("/".join(parts[:4]), set()).add(parts[4])
    dated = {}
    for folder in folders:
        try:
            d = json.loads(files[folder + "/meta.json"].decode("utf-8"))
            dated[folder.split("/")[3]] = datetime.fromisoformat(d["publish_at"])
        except Exception:  # reported per post below
            pass
    seen = {}
    for folder in sorted(folders):
        slug = folder.split("/")[3]
        if slug in seen:
            errors.append("%s: duplicate slug (also %s)" % (folder, seen[slug]))
        seen[slug] = folder
        missing = REQUIRED_FILES - folders[folder]
        if missing:
            errors.append("%s: missing %s" % (folder, ", ".join(sorted(missing))))
            continue
        try:
            meta = json.loads(files[folder + "/meta.json"].decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            errors.append("%s/meta.json: not valid JSON (%s)" % (folder, e))
            continue
        errs = check_meta(meta, folder, files)
        errors += ["%s: %s" % (folder, e) for e in errs]
        stream = meta.get("stream") if isinstance(meta, dict) else None
        when = dated.get(slug)
        errs, _ = check_post_html(files[folder + "/post.html"], links, stream if stream in WORDS else "editorial",
                                  dated, when)
        errors += ["%s/post.html: %s" % (folder, e) for e in errs]
        if folder + "/post.en.html" in files:
            errs, _ = check_post_html(files[folder + "/post.en.html"], links, None, dated, when)
            errors += ["%s/post.en.html: %s" % (folder, e) for e in errs]
        errors += ["%s: %s" % (folder, e) for e in check_svg(files[folder + "/cover.svg"])]
        errors += ["%s: %s" % (folder, e) for e in check_png(files[folder + "/cover.png"])]
    if check_feed and not errors:
        try:
            fresh = build_feed.build(files)
            ET.fromstring(fresh)
        except Exception as e:  # any failure to build is a gate failure
            errors.append("feed.xml: build failed (%s)" % e)
        else:
            if files.get("feed.xml") != fresh:
                errors.append("feed.xml: out of date - run tools/build_feed.py and commit the result")
    return errors


# ---------------------------------------------------------------- selftest
def _selftest(files):
    clean = dict(files)
    clean["feed.xml"] = build_feed.build(clean)
    real = sorted(r[:-len("/meta.json")] for r in clean if r.startswith("posts/") and r.endswith("/meta.json"))
    ok = True
    errs = validate(clean)
    print("%s real posts (%d): %s" % ("PASS" if not errs else "FAIL", len(real), ", ".join(p.split("/")[-1] for p in real)))
    for e in errs:
        print("   ", e)
    ok &= not errs and len(real) >= 2
    by_date = sorted(real, key=lambda p: build_feed.parse_time(json.loads(clean[p + "/meta.json"])["publish_at"]))
    target = next(p for p in by_date if json.loads(clean[p + "/meta.json"])["stream"] == "editorial")
    later = by_date[-1].split("/")[3]

    def post(fn):
        def m(t):
            t[target + "/post.html"] = fn(t[target + "/post.html"].decode("utf-8")).encode("utf-8")
        return m

    def svg(fn):
        def m(t):
            t[target + "/cover.svg"] = fn(t[target + "/cover.svg"].decode("utf-8")).encode("utf-8")
        return m

    def meta(fn):
        def m(t):
            d = json.loads(t[target + "/meta.json"])
            fn(d)
            t[target + "/meta.json"] = json.dumps(d, ensure_ascii=False).encode("utf-8")
        return m

    def svg_inject(s):
        return lambda t: t.replace("</defs>", "</defs>" + s, 1)

    def dup(t):
        d = json.loads(t[target + "/meta.json"])
        d["publish_at"] = "2027-01-05T08:00:00+03:30"
        new = "posts/2027/01/" + d["slug"]
        for name in ("post.html", "cover.svg", "cover.png"):
            t[new + "/" + name] = t[target + "/" + name]
        t[new + "/meta.json"] = json.dumps(d, ensure_ascii=False).encode("utf-8")

    def move(t):
        d = json.loads(t[target + "/meta.json"])
        d["publish_at"] = "2026-12-05T08:00:00+03:30"
        t[target + "/meta.json"] = json.dumps(d, ensure_ascii=False).encode("utf-8")

    def product(t):
        d = json.loads(t[target + "/meta.json"])
        d.update(stream="product", category="product", category_fa="محصول", category_en="Product",
                 release_ref="releases/2026-11-01-missing.md")
        t[target + "/meta.json"] = json.dumps(d, ensure_ascii=False).encode("utf-8")

    def png_size(t):
        b = bytearray(t[target + "/cover.png"])
        b[16:20] = (1000).to_bytes(4, "big")
        t[target + "/cover.png"] = bytes(b)

    def stale(t):
        t["feed.xml"] = t["feed.xml"].replace(b"</channel>", b"<!-- edited -->\n</channel>")

    first_p = "<p>"

    def three_post_links(t):
        newest = by_date[-1]
        link = '<a href="/blog/%s/">x</a> ' % target.split("/")[3]
        t[newest + "/post.html"] = t[newest + "/post.html"].decode("utf-8").replace(
            first_p, "<p>" + link * 3, 1).encode("utf-8")
    fixtures = [
        ("<script> in a post", "tag not allowed: <script>", post(lambda t: t.replace(first_p, "<script>alert(1)</script>" + first_p, 1))),
        ("onclick on a tag", "attribute not allowed: onclick", post(lambda t: t.replace(first_p, '<p onclick="steal()">', 1))),
        ("http:// link", "href not allowed", post(lambda t: t.replace(first_p, '<p><a href="http://example.com/">x</a> ', 1))),
        ("javascript: link", "href not allowed", post(lambda t: t.replace(first_p, '<p><a href="javascript:alert(1)">x</a> ', 1))),
        ("entity decoding to <script", "decodes to '<script'", post(lambda t: t.replace(first_p, "<p>&lt;script&gt; ", 1))),
        ("HTML comment", "comment not allowed", post(lambda t: t.replace(first_p, "<!-- x -->" + first_p, 1))),
        ("']]>' in a post", "']]>' not allowed", post(lambda t: t.replace(first_p, "<p>]]> ", 1))),
        ("link outside site-links.txt", "href not allowed", post(lambda t: t.replace(first_p, '<p><a href="/wp-admin/">x</a> ', 1))),
        ("two plavia.ir links", "at most one link", post(lambda t: t.replace(first_p, '<p><a href="/pricing/">a</a> <a href="https://plavia.ir/demo/">b</a> ', 1))),
        ("img tag in a post", "tag not allowed: <img>", post(lambda t: t.replace(first_p, '<p><img src="https://example.com/a.png"> ', 1))),
        ("link to a post that does not exist", "does not exist", post(lambda t: t.replace(first_p, '<p><a href="/blog/no-such-post/">x</a> ', 1))),
        ("link to a later-dated post", "not dated earlier", post(lambda t: t.replace(first_p, '<p><a href="/blog/%s/">x</a> ' % later, 1))),
        ("link to the post itself", "not dated earlier", post(lambda t: t.replace(first_p, '<p><a href="/blog/%s/">x</a> ' % target.split("/")[3], 1))),
        ("three links to earlier posts", "at most 2 links to earlier posts", three_post_links),
        ("SVG with onload", "attribute not allowed: onload", svg(lambda t: t.replace("<svg ", '<svg onload="alert(1)" ', 1))),
        ("SVG with an external href", "attribute not allowed: href", svg(svg_inject('<rect href="https://example.com/x.svg" width="1" height="1"/>'))),
        ("SVG with an external xlink:href", "attribute not allowed: {http://www.w3.org/1999/xlink}href",
         svg(lambda t: t.replace("<svg ", '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1).replace("</defs>", '</defs><use xlink:href="https://example.com/x.svg#a"/>', 1))),
        ("SVG <image>", "element not allowed", svg(svg_inject('<image href="https://example.com/a.png" width="10" height="10"/>'))),
        ("SVG with a DOCTYPE entity", "DOCTYPE", svg(lambda t: '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "y">]>' + t)),
        ("SVG style attribute", "attribute not allowed: style", svg(svg_inject('<rect style="fill:red" width="1" height="1"/>'))),
        ("SVG url() to a remote file", "url() must be url(#local-id)", svg(svg_inject('<rect fill="url(https://example.com/p.svg#g)" width="1" height="1"/>'))),
        ("SVG <text>", "element not allowed", svg(svg_inject("<text>hi</text>"))),
        ("missing focus_queries", "missing focus_queries", meta(lambda d: d.pop("focus_queries"))),
        ("four focus queries", "focus_queries must hold 1-3", meta(lambda d: d.update(focus_queries=["الف ب", "پ ت", "ث ج", "چ ح"]))),
        ("duplicate focus query", "duplicate focus query", meta(lambda d: d.update(focus_queries=["الف ب", "الف ب"]))),
        ("66-character seo_title", "seo_title is 66 characters", meta(lambda d: d.update(seo_title="ا" * 66))),
        ("69-character meta_description", "must be 70-160", meta(lambda d: d.update(meta_description="ا" * 69))),
        ("excerpt of 161 characters", "excerpt is 161 characters", meta(lambda d: d.update(excerpt="ا" * 161))),
        ("duplicate slug", "duplicate slug", dup),
        ("editorial post with one source", "at least 2 sources", meta(lambda d: d.update(sources=d["sources"][:1]))),
        ("http:// source", "source url must be https", meta(lambda d: d["sources"][0].update(url="http://example.com/"))),
        ("unknown category", "not in", meta(lambda d: d.update(category="news"))),
        ("wrong category name", "must be named", meta(lambda d: d.update(category_fa="راهنما"))),
        ("publish_at without offset", "publish_at must be ISO 8601", meta(lambda d: d.update(publish_at="2026-11-14T08:00:00"))),
        ("folder does not match publish_at", "does not match publish_at", move),
        ("bad slug", "bad slug", meta(lambda d: d.update(slug="Bad_Slug"))),
        ("unknown meta key", "unknown key", meta(lambda d: d.update(word_count=1000))),
        ("tag with a comma", "bad tag", meta(lambda d: d["tags"].append("a,b"))),
        ("product post without its release file", "release_ref", product),
        ("cover.png not 1200x630", "must be 1200x630", png_size),
        ("feed.xml not rebuilt", "feed.xml: out of date", stale),
    ]
    rejected = 0
    for name, expect, mutate in fixtures:
        t = dict(clean)
        mutate(t)
        errs = validate(t, check_feed=(mutate is stale))
        hit = [e for e in errs if expect in e]
        if hit:
            rejected += 1
            print("REJECTED  %-40s %s" % (name, hit[0]))
        else:
            ok = False
            print("ACCEPTED  %-40s expected an error containing %r; got %s" % (name, expect, errs or "none"))
    t = dict(clean)  # a link from the newest post to an earlier one must be accepted
    newest = by_date[-1]
    t[newest + "/post.html"] = t[newest + "/post.html"].decode("utf-8").replace(
        first_p, '<p><a href="/blog/%s/">x</a> ' % target.split("/")[3], 1).encode("utf-8")
    errs = validate(t, check_feed=False)
    ok &= not errs and newest != target
    print("%s  %-40s %s" % ("PASSED  " if not errs else "REJECTED", "link to an earlier post (must pass)", errs or "ok"))
    print("selftest: %d/%d bad fixtures rejected, real posts %s" % (rejected, len(fixtures), "pass" if not validate(clean) else "FAIL"))
    return ok and rejected == len(fixtures)


def main(argv):
    root = os.path.dirname(HERE)
    files = build_feed.load_tree(root)
    if "--selftest" in argv:
        return 0 if _selftest(files) else 1
    errors = validate(files)
    for e in errors:
        print(e)
    if errors:
        return 1
    posts = sum(1 for r in files if r.startswith("posts/") and r.endswith("/meta.json"))
    print("ok: %d posts, feed.xml up to date" % posts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
