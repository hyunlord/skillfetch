# Knowledge gap: what the model answers without the skill

Measured 2026-10-27. No skill was loaded in any call.

## Method

- **Candidates (30):** skills in the released index (index-2026-10-24, 2,281 canonical) whose descriptions name a library or framework version or a 2025–2026 change, an external service or API, or a public spec's detailed rules. They were picked by keyword scoring and then by reading; each skill's file was checked for the fact its description promises. List: `candidates.jsonl` (kind V = version or change, S = service or API, P = public spec; `evidence` quotes the description).
- **Questions (60):** 2 per candidate, each with a short answer taken from the skill's file (`questions.py`, with the accepted answer pattern).
- **Official check:** each answer was compared with official documentation, the spec, or the npm registry (`verified.py`): confirmed 47, partial 12 (consistent but not confirmed by an official page), not confirmed 1.
- **Calls:** each question 3 times, one isolated `claude -p` per call (model `claude-opus-5-5`, no tools, no MCP servers, project settings only, a neutral working directory). The system prompt asks for the specific answer and a confidence. 180 calls, 0 errors, $0.878 API-price equivalent.
- **Grading:** the answer pattern against the model's answer; every answer was also read. Rows: `answers.jsonl` (answer, confidence, correct).

## Result

**173 of 180 answers were correct.**

| # | skill | kind | correct | per question (correct/3, official check) |
|---|---|---|---:|---|
| 1 | uasl/next-cache-components | V | 6/6 | 1a 3/3 (confirmed); 1b 3/3 (confirmed) |
| 2 | affaan-m-ecc/nextjs-turbopack | V | 6/6 | 2a 3/3 (confirmed); 2b 3/3 (confirmed) |
| 3 | uasl/tailwind-theme-builder | V | 6/6 | 3a 3/3 (confirmed); 3b 3/3 (confirmed) |
| 4 | affaan-m-ecc/nuxt4-patterns | V | 6/6 | 4a 3/3 (confirmed); 4b 3/3 (confirmed) |
| 5 | affaan-m-ecc/rails-patterns | V | 6/6 | 5a 3/3 (partial); 5b 3/3 (partial) |
| 6 | affaan-m-ecc/swift-concurrency-6-2 | V | 6/6 | 6a 3/3 (partial); 6b 3/3 (confirmed) |
| 7 | rshankras-claude-code-apple-skills/swift-concurrency-updates | V | 6/6 | 7a 3/3 (confirmed); 7b 3/3 (partial) |
| 8 | rshankras-claude-code-apple-skills/memory | V | 6/6 | 8a 3/3 (confirmed); 8b 3/3 (partial) |
| 9 | rshankras-claude-code-apple-skills/liquid-glass | V | 6/6 | 9a 3/3 (confirmed); 9b 3/3 (confirmed) |
| 10 | affaan-m-ecc/foundation-models-on-device | V | 6/6 | 10a 3/3 (confirmed); 10b 3/3 (confirmed) |
| 11 | rshankras-claude-code-apple-skills/alarmkit | V | 6/6 | 11a 3/3 (confirmed); 11b 3/3 (confirmed) |
| 12 | ahmed3elshaer-everything-claude-code-mobile/m3-expressive | V | 6/6 | 12a 3/3 (partial); 12b 3/3 (partial) |
| 13 | uasl/claude-native-claude-api | V | 6/6 | 13a 3/3 (partial); 13b 3/3 (confirmed) |
| 14 | anthropics-skills/claude-api | S | 3/6 | 14a 3/3 (confirmed); 14b 0/3 (confirmed) |
| 15 | uasl/stripe-best-practices | S | 6/6 | 15a 3/3 (confirmed); 15b 3/3 (confirmed) |
| 16 | rshankras-claude-code-apple-skills/external-purchases | S | 6/6 | 16a 3/3 (confirmed); 16b 3/3 (confirmed) |
| 17 | rshankras-claude-code-apple-skills/ad-attribution | S | 5/6 | 17a 3/3 (partial); 17b 2/3 (confirmed) |
| 18 | rshankras-claude-code-apple-skills/iap-finalizer | S | 6/6 | 18a 3/3 (confirmed); 18b 3/3 (partial) |
| 19 | rshankras-claude-code-apple-skills/subscription-offers | S | 6/6 | 19a 3/3 (confirmed); 19b 3/3 (confirmed) |
| 20 | rshankras-claude-code-apple-skills/privacy-manifests | S | 6/6 | 20a 3/3 (confirmed); 20b 3/3 (confirmed) |
| 21 | uasl/using-neon | S | 6/6 | 21a 3/3 (confirmed); 21b 3/3 (confirmed) |
| 22 | uasl/cf-crawl | S | 6/6 | 22a 3/3 (confirmed); 22b 3/3 (confirmed) |
| 23 | uasl/mcp-server-patterns | S | 6/6 | 23a 3/3 (confirmed); 23b 3/3 (partial) |
| 24 | uasl/owasp-security | P | 6/6 | 24a 3/3 (confirmed); 24b 3/3 (confirmed) |
| 25 | uasl/llm-security | P | 6/6 | 25a 3/3 (confirmed); 25b 3/3 (confirmed) |
| 26 | affaan-m-ecc/accessibility | P | 6/6 | 26a 3/3 (confirmed); 26b 3/3 (confirmed) |
| 27 | uasl/global-privacy-control | P | 6/6 | 27a 3/3 (confirmed); 27b 3/3 (confirmed) |
| 28 | uasl/hipaa-breach-notify | P | 6/6 | 28a 3/3 (confirmed); 28b 3/3 (confirmed) |
| 29 | affaan-m-ecc/nodejs-keccak256 | P | 6/6 | 29a 3/3 (confirmed); 29b 3/3 (confirmed) |
| 30 | uasl/ai-dpia | P | 3/6 | 30a 0/3 (not confirmed); 30b 3/3 (partial) |

## Wrong answers

| question | runs | answer | confidence | official answer |
|---|---|---|---|---|
| 14b Claude Opus 5.5 input price per million tokens | 3 of 3 | "$5 per million input tokens (best guess: Opus 4.5 was priced at $5 …)" | 0.3 | $4 (platform.claude.com model page; anthropic.com) |
| 17b iOS version that added AdAttributionKit conversion tags | 1 of 3 | "iOS 18.0" | 0.6 | iOS 18.4 (Apple, AdAttributionKit conversion tags) |
| 30a EDPB document on processing personal data through AI systems | 3 of 3 | "EDPB Opinion 28/2024 …" | 0.3 | see below |

- **Wrong without the skill, and the skill has the confirmed answer:** 14b (`anthropics-skills/claude-api`, whose model table lists Opus 5.5 at $4.00), and partly 17b (`rshankras-claude-code-apple-skills/ad-attribution`, 1 run of 3). No question was asked with the skill loaded.
- **30a:** the `uasl/ai-dpia` skill cites "EDPB Guidelines 04/2025 on processing personal data through AI systems". The document was not found in the EDPB's list of guidelines, which shows 01/2025, 02/2025 and 3/2025. The model's answer names the EDPB's Opinion 28/2024 on AI models. The skill's citation may be wrong.

## Limits

- Short factual questions. They do not measure whether the model applies the fact while coding.
- One model, 3 runs per question, 2 questions per candidate.
- The candidates were chosen from descriptions; skills outside the 30 were not asked about.
