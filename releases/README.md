# releases/ - the product-updates stream

Posts in the `product` stream (category `product`, «محصول») are written ONLY from a file in this folder.

- Files here are added by the Plavia team, never by the writing agent. One file per release or update, named
  `YYYY-MM-DD-<short-name>.md`, holding verified facts only: what was shipped, where it is installed, what a user can
  now do, and what is not connected yet.
- The writer turns one file into one post and sets `release_ref` in the post's `meta.json` to that file's path
  (for example `releases/2026-12-01-invoice-reminders.md`). `tools/validate.py` rejects a product post whose
  `release_ref` does not name an existing file here.
- Nothing that is not in the file goes into the post: no facts from the web, from memory or from guesses. An
  integration that is not connected yet is described as "ready to connect", never as working.

There is no release file yet.
