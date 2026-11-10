"""Build feed.xml (RSS 2.0 + content:encoded + plavia:) from posts/.

Stdlib only, Python 3.9+. Deterministic: the same posts give byte-identical output (no clock is read).
Usage, from the repository root:  python tools/build_feed.py
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape, quoteattr

MAX_ITEMS = 60
SITE = "https://plavia.ir"
RAW = "https://raw.githubusercontent.com/rohnikan-tech/plavia-blog-feed/main/"
NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"
NS_PLAVIA = "https://plavia.ir/ns/blog-feed/1"


def load_tree(root):
    """Every file the feed and the validator read, as {posix relative path: bytes}."""
    files = {}
    for top in ("posts", "releases"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, top)):
            dirnames.sort()
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                with open(full, "rb") as f:
                    files[rel] = f.read()
    for name in ("site-links.txt", "feed.xml"):
        full = os.path.join(root, name)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                files[name] = f.read()
    return files


def parse_time(value):
    return datetime.fromisoformat(value)


def rfc822(dt):
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def cdata(text):
    if "]]>" in text:
        raise ValueError("']]>' cannot be placed in CDATA")
    return "<![CDATA[" + text + "]]>"


def collect_posts(files):
    posts = []
    for rel in sorted(files):
        parts = rel.split("/")
        if len(parts) == 5 and parts[0] == "posts" and parts[4] == "meta.json":
            folder = "/".join(parts[:4])
            meta = json.loads(files[rel].decode("utf-8"))
            posts.append((folder, meta))
    posts.sort(key=lambda p: (parse_time(p[1]["publish_at"]), p[1]["slug"]), reverse=True)
    return posts


def build(files):
    posts = collect_posts(files)
    items = posts[:MAX_ITEMS]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:content=%s xmlns:plavia=%s>' % (quoteattr(NS_CONTENT), quoteattr(NS_PLAVIA)),
           "<channel>",
           "<title>%s</title>" % escape("بلاگ پلاویا"),
           "<link>%s/blog/</link>" % SITE,
           "<description>%s</description>" % escape("آموزش هوش مصنوعی، فناوری و گجت برای کسب‌وکارهای کوچک"),
           "<language>fa</language>"]
    if posts:
        out.append("<lastBuildDate>%s</lastBuildDate>" % rfc822(parse_time(posts[0][1]["publish_at"])))
    for folder, m in items:
        cover = folder + "/cover.png"
        png = files[cover]
        tags = ",".join(m["tags"])
        out += ["<item>",
                "<title>%s</title>" % escape(m["title"]),
                "<link>%s/blog/%s/</link>" % (SITE, m["slug"]),
                '<guid isPermaLink="false">%s</guid>' % escape(m["slug"]),
                "<pubDate>%s</pubDate>" % rfc822(parse_time(m["publish_at"])),
                '<category domain="plavia">%s</category>' % escape(m["category"]),
                "<description>%s</description>" % escape(m["excerpt"]),
                "<content:encoded>%s</content:encoded>" % cdata(files[folder + "/post.html"].decode("utf-8")),
                '<enclosure url=%s length="%d" type="image/png"/>' % (quoteattr(RAW + cover), len(png))]
        fields = [("slug", m["slug"]), ("lang", m["lang"]), ("stream", m["stream"]),
                  ("category_fa", m["category_fa"]), ("category_en", m["category_en"]), ("tags", tags),
                  ("seo_title", m["seo_title"]), ("focus_queries", " | ".join(m["focus_queries"])),
                  ("meta_description", m["meta_description"]), ("published_at", m["publish_at"]),
                  ("reading_minutes", str(m["reading_minutes"])), ("cover_path", cover),
                  ("cover_sha256", hashlib.sha256(png).hexdigest()), ("cover_alt", m["cover_alt"]),
                  ("revision", str(m["revision"]))]
        for key in ("title_en", "excerpt_en"):
            if key in m:
                fields.append((key, m[key]))
        for key, value in fields:
            out.append("<plavia:%s>%s</plavia:%s>" % (key, escape(value), key))
        en = folder + "/post.en.html"
        if en in files:
            out.append("<plavia:content_en>%s</plavia:content_en>" % cdata(files[en].decode("utf-8")))
        out.append("</item>")
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out).encode("utf-8")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = build(load_tree(root))
    with open(os.path.join(root, "feed.xml"), "wb") as f:
        f.write(data)
    print("feed.xml: %d bytes" % len(data))


if __name__ == "__main__":
    sys.exit(main())
