# plavia-blog-feed

## فارسی

این مخزن منبع محتوای بلاگ [پلاویا](https://plavia.ir/blog/) است: نوشته‌های نهایی (آموزش هوش مصنوعی، فناوری و گجت،
و تازه‌های محصول) همراه با تصویر جلد برداری هر نوشته و یک فید (`feed.xml`). اینجا فقط محتوای آمادهٔ انتشار نگه داشته
می‌شود؛ هیچ کد سایت، رمز یا اطلاعات شخصی در این مخزن نیست.

© پلاویا - انتشار دوبارهٔ متن‌ها و تصویرها بدون اجازه مجاز نیست.

سایت plavia.ir این فید را با زمان‌بندی خودش می‌خواند، همهٔ محتوا را دوباره پاک‌سازی می‌کند و هر نوشته را از زمان
`publish_at` آن نمایش می‌دهد. نوشته‌هایی که تاریخشان هنوز نرسیده در فید هستند اما پیش از آن تاریخ نمایش داده نمی‌شوند.

## English

This repository is the content source of the [Plavia blog](https://plavia.ir/blog/): finished posts (AI tutorials,
technology and gadget explainers, product updates), a vector cover for each post, and a feed (`feed.xml`). It holds
publish-ready content only - no site code, no credentials, no personal data.

(c) Plavia - text and illustrations may not be republished without permission.

How the feed is consumed: plavia.ir pulls `feed.xml` on its own schedule (from this repository's raw URL or a mirror
such as jsDelivr), treats it as untrusted input and sanitises it again, resolves `plavia:cover_path` against the
mirror it fetched from, and shows each post once its `publish_at` time has arrived; future-dated posts are already
in the feed. `tools/validate.py` is the first gate and runs on every push; `tools/build_feed.py` regenerates the
feed. Posts live in `posts/YYYY/MM/<slug>/` (`post.html`, `meta.json`, `cover.svg`, `cover.png`). The writing rules
are in `AGENT.md`, the cover rules in `illustration-system.md`.
