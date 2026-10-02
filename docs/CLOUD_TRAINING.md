# Private Cloud Training Providers

AI Brain can optionally use one cloud model as a **teacher** to refine an explicitly selected, approved local dataset. The refined examples are stored locally and can then be used by the existing local LoRA workflow or retained as local training data.

## Privacy boundary

- Only one provider can be active at a time.
- API keys are encrypted in the local vault and are never returned by the API/UI.
- Cloud teacher code has no automatic access to conversations, Memory, the full Brain database, local files, Google data, or MCP data.
- Only approved items from the dataset the user explicitly selects are sent.
- Provider output is saved back to that local dataset.
- Cloud mode requires network access. Offline inference never needs the provider key.
- A cloud request necessarily sends the selected example to that provider. Provider-side retention is controlled by the provider's own policy/account settings; AI Brain cannot guarantee zero provider-side retention.

## Providers

- **OpenAI API** — OpenAI-compatible Chat Completions endpoint.
- **Ollama Cloud** — OpenAI-compatible Ollama Cloud endpoint.
- **OpenAI-compatible Cloud** — custom HTTPS base URL.

ChatGPT account/subscription credentials are not supported or requested. Use an API key issued for API access.

## CLI

```bash
python scripts/ai_brain_cli.py cloud-training-status
python scripts/ai_brain_cli.py cloud-training-config openai --api-key "YOUR_KEY" --model "MODEL" --activate
python scripts/ai_brain_cli.py cloud-training-config ollama_cloud --api-key "YOUR_KEY" --model "gpt-oss:120b-cloud" --activate
python scripts/ai_brain_cli.py cloud-training-config compatible --base-url "https://provider.example/v1" --api-key "YOUR_KEY" --model "MODEL" --activate
python scripts/ai_brain_cli.py cloud-training-distill DATASET_ID
```

Prefer entering keys interactively in the Web UI where practical: command-line arguments can be visible in shell history/process listings.
