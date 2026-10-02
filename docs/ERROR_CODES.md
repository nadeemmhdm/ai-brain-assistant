# AI Brain Error Codes

Stable error codes make failures searchable across the Web UI, CLI, logs, issues, and documentation.

## Format

`AIB-COMPONENT-NNN`

| Prefix | Component |
|---|---|
| `GEN` | General/runtime |
| `NET` | Network |
| `AUTH` | Authentication |
| `MDL` | Models / Hugging Face |
| `LRN` | Trusted Topic Learning |
| `BRN` | AI Brain knowledge |
| `TRN` | Fine-tuning/training |
| `UPD` | Installer/updater |

## Registry

| Code | Meaning | What to do |
|---|---|---|
| `AIB-GEN-001` | Unexpected internal error | Retry once, then inspect the backend log. |
| `AIB-NET-001` | Internet service unreachable | Check connectivity or continue offline. |
| `AIB-AUTH-001` | Authentication required | Unlock AI Brain and retry. |
| `AIB-MDL-001` | Local model server unavailable | Start/load llama.cpp model server. |
| `AIB-MDL-002` | Invalid model request | Check model path, filename and role. |
| `AIB-MDL-003` | Hugging Face unreachable | Check internet connectivity. |
| `AIB-MDL-004` | Invalid Hugging Face token | Verify token and permissions. |
| `AIB-LRN-001` | Invalid learning topic | Use a topic of 1–200 characters. |
| `AIB-LRN-002` | Learning session already active | Finish/cancel the active session. |
| `AIB-LRN-003` | Unknown learning session | Refresh and verify session ID. |
| `AIB-BRN-001` | Invalid Brain knowledge input | Provide a valid question and answer. |
| `AIB-TRN-001` | Unknown training job | Refresh Training and verify job ID. |
| `AIB-UPD-001` | Update cannot be safely installed | Check Git/network/local changes. |

## API shape

Errors using the registry return a stable payload inside FastAPI's `detail` field:

```json
{
  "detail": {
    "code": "AIB-LRN-002",
    "message": "Another Trusted Topic Learning session is already running.",
    "hint": "Wait, pause/cancel the active session, then retry."
  }
}
```

Applications should branch on `code`, not the human-readable message. Codes are intended to remain stable even if wording changes.
