# intent/

One folder per change: `intent/<YYYY-MM-DD>-<slug>/`. Each stage records (commits, via
`sdlc/record.sh`) a file the next stage reads, so the folder plus its history is the record of who asked, what was
decided and who approved it.

| File | Stage | Written by | Accepted when |
|---|---|---|---|
| `intent.md` | 1 Plan | `/intent` | Status: accepted, recorded |
| `spec.md` | 2 Design | `/spec` | Status: approved, recorded |
| `plan.md` | 3 Build | `/implement` (from plan mode) | accepted plan, recorded before coding |

Delivery metrics for these folders: `python3 sdlc/delivery.py`.
