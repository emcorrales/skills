# intent/

One folder per change: `intent/<YYYY-MM-DD>-<slug>/`. Each stage commits a file the next
stage reads, so the folder plus its git history is the record of who asked, what was
decided and who approved it.

| File | Stage | Written by | Accepted when |
|---|---|---|---|
| `intent.md` | 1 Plan | `/intent` | Status: accepted, committed |
| `spec.md` | 2 Design | `/spec` | Status: approved, committed |
| `plan.md` | 3 Build | `/implement` (from plan mode) | approved plan, committed with the code |

Delivery metrics for these folders: `python3 sdlc/delivery.py`.
