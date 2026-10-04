# Platform spike (#39)

Date: 2026-10-04 (UTC). Four platform unknowns settled before the dependent leaves (#57, #11, #63, #47, #55, #66, #68) are written. Nothing production was changed. Secrets are redacted in all evidence below.

| # | Question | Decision |
|---|----------|----------|
| 1 | Real post-call payload shape | Fixture in webhook shape committed: `hotline/tests/fixtures/post_call_transcription.json` |
| 2 | Keypad (DTMF) PIN | Keypad PIN first with spoken fallback. Delivery on a Twilio-imported number is documented but not yet observed live: confirm in #56 |
| 3 | Agent Tests API | Usable on our plan. #55 uses it, no WebSocket fallback needed |
| 4 | BackgroundTasks on Vercel Python | Reliable for a 20 s task. #68 sweeper stays as a safety net, not a critical-path blocker |

## 1. Post-call payload and fixture

**Tried.** Opened a text-only WebSocket conversation on the draft agent (`wss://api.elevenlabs.io/v1/convai/conversation?agent_id=…`, init message `conversation_config_override.conversation.text_only = true`, which the agent allows). Four Kiswahili user turns, 9 transcript turns in total. Then `GET /v1/convai/conversations/{id}` (status `done` after about 20 s).

**Evidence.** The fixture holds the real values from that conversation. Wrapper per the docs (https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks): `{type: "post_call_transcription", event_timestamp, data}`.

Verified in the docs (data table): `agent_id, agent_name, conversation_id, status, user_id, branch_id, version_id, environment, transcript, metadata, analysis, conversation_initiation_client_data, has_audio, has_user_audio, has_response_audio`. Docs example turns carry `tool_calls: null`.

Derived from the GET (not confirmed against a real webhook delivery):

- Turn fields beyond the docs example (`interrupted`, `source_medium`, `producing_llm`, `llm_usage`, `reasoning`, …) come from the GET. The webhook uses the same `ConversationHistoryCommonModel`, so they are probably present, but #11 must ignore unknown fields.
- GET returned `tool_calls: []` and `tool_results: []`. The docs example shows `null`. Receivers must treat `null` and `[]` the same.
- I removed from the GET body: top-level extras not in the docs data table (`conversation_product`, `visited_agents`, `tag_ids`, `orchestrator`, `otlp_traces`, …), per-turn `agent_metadata`, `metadata.features_usage` and `batch_call`, and `dynamic_variables.system__conversation_history` (duplicates the transcript).
- `event_timestamp` is synthetic: `start_time_unix_secs + call_duration_secs + 5`.

**Gaps for later leaves.**

- The draft agent has **no tools**, so every turn has empty `tool_calls`/`tool_results`. The documented tool shapes (GET reference, https://elevenlabs.io/docs/eleven-agents/api-reference/conversations/get): `tool_calls[] {request_id, tool_name, params_as_json (a string), tool_has_been_called, type}` and `tool_results[] {request_id, tool_name, result_value, is_error, tool_has_been_called}`. #57 and #63 should build tool turns from that, not from the fixture.
- A phone call fills `metadata.phone_call` and `system__caller_id`/`system__called_number`/`system__call_sid`. The fixture has them as `null` and a text call can't show their real shape.
- The analysis summary is in English although the call is Kiswahili. Data collection is not configured, so `data_collection_results` is empty.

**Scrubbing.** Nulled: `user_id`, `metadata.phone_call`, `system__caller_id`, `system__called_number`, `system__call_sid`, `system__call_id`, `system__user_id`, `system__initiator_id`. No PIN appears in any turn (the farmer never said one). Floats rounded to 4 decimals.

**Gotcha for the grep check.** The three unix timestamps (`event_timestamp`, `start_time_unix_secs`, `accepted_time_unix_secs`) are 10 digits, so a bare `[0-9]{9,}` grep matches them and they cannot be removed without breaking the shape. Everything else is clean. Suggested test for #57 (not committed here): `test_fixture_has_no_phone_numbers`, asserting no `\+\d{6,}` and no run of 9+ digits outside keys ending in `_unix_secs` or `event_timestamp`.

## 2. DTMF (keypad PIN)

**Tried.** Created a throwaway agent (`POST /v1/convai/agents/create`), then:

```
PATCH /v1/convai/agents/{throwaway}
{"conversation_config":{"conversation":{"dtmf_input_settings":
  {"dtmf_input_timeout":3.0,"hash_terminator":true,"redact_input":true}}}}
```

Response 200, and a follow-up GET returns `{'dtmf_input_timeout': 3.0, 'hash_terminator': True, 'redact_input': True}`. The production agent's `dtmf_input_settings` stayed `null`.

**Evidence from the docs** (https://elevenlabs.io/docs/eleven-agents/customization/multimodal-input):

- Only **out-of-band** DTMF from the Twilio native integration, SIP trunking or Genesys is supported. In-band tones are ignored. Web widget and chat cannot send DTMF.
- A keypad sequence ends on `#` or after `dtmf_input_timeout` and becomes one user turn. The first key interrupts the agent.
- `redact_input: true` replaces keypad digits with `<REDACTED>` in the stored transcript, conversation log and analysis. It does **not** hide them from the agent during the call, nor digits the agent speaks back or sends to a tool.
- A GET shows `source_medium` can be `dtmf`, so keypad turns are identifiable.

**Not verified.** Live delivery of keys on a Twilio-imported number. The number is not imported into ElevenLabs (that is #56, outside this leaf) and text/WebSocket conversations cannot send DTMF. The old TwiML route (`twilio_line`) never reaches the agent. "Twilio-imported" means the native integration.

**Decision.** #47 writes the prompt for **keypad PIN first, spoken PIN as fallback** (and when a digit string arrives either way, same `identify_farmer` path). `sync_agent.py` sets `dtmf_input_settings` with `redact_input: true`. Consequence of the redaction limits: our §7 PIN redaction to `[PIN]` must still run, because spoken digits, agent read-backs and tool params are not covered. #56 must make a real call with keypad digits and check for a `dtmf` turn; if none arrives, the demo uses the spoken PIN.

## 3. Agent Tests API

**Tried**, on the throwaway agent (tests are workspace-level):

| Call | Result |
|------|--------|
| `GET /v1/convai/agent-testing?page_size=5` | 200 `{"tests":[],…}` |
| `POST /v1/convai/agent-testing/create` (name, `chat_history`, `success_condition`, one success and one failure example) | 200 `{"id":"test_…"}` |
| `POST /v1/convai/agents/{id}/run-tests` body `{"tests":[{"test_id":"…"}]}` | 200, suite id `suite_…`, test run `pending` |
| `GET /v1/convai/test-invocations/{suite_id}` after 25 s | 200, run `passed`, `condition_result.result: "success"`, rationale text |

No 403 on our Creator plan. The run executed against the agent's version snapshot (`ran_against_draft: false`).

**Decision.** Agent Tests are usable. #55 uses create-test, run-tests and test-invocations; a text-only WebSocket conversation is only a backup. Tests created are workspace objects: #55 should name them with a `hotline-` prefix. Tool-using tests were not tried (the throwaway had no tools).

## 4. BackgroundTasks on Vercel Python

**Tried.** `vercel deploy --yes` of a temp folder (`app.py` with FastAPI, `requirements.txt`, `vercel.json` `{}`) to a new throwaway project. Route `GET /probe` returns JSON at once and schedules `BackgroundTasks` that prints `bg_start`, sleeps 20 s, prints `bg_done` (UTC timestamps). Called through `vercel curl` (it mints a protection bypass token itself). Logs read with `vercel logs … --expand`.

**Evidence** (runtime logs, three requests, one cold):

```
PROBE responding tag=b t=2026-10-04T02:55:22.898611+00:00     client total 0.46 s, HTTP 200
PROBE bg_start   tag=b t=2026-10-04T02:55:22.899357+00:00
PROBE bg_done    tag=b t=2026-10-04T02:55:42.899570+00:00     20.0 s after the response
```

Tags `a` and `c` behave the same (`bg_done` exactly 20 s after the response). The client got 200 before the work finished each time.

**Caveats.** Only a 20 s task, on a light load; the project had no custom `maxDuration`. The CLI created the probe's first deployment with target `production` (first deploy of a new project), so no preview deployment was exercised. The URL stayed protected and was reached with the bypass token. Longer work (the Opus extraction can exceed 20 s) is not proven; it is bounded by the function's `maxDuration`.

**Decision.** BackgroundTasks run to completion after the response on Vercel Python, so #66 can enqueue the pipeline in a background task. The #68 sweeper does **not** join the critical path, but stays as a backstop for tasks cut off by `maxDuration`, crashes and retries. #66 should set `maxDuration` explicitly and log start/finish per call.

## Cleanup and production safety

- Throwaway ElevenLabs agent `spike-39-throwaway`: created, PATCHed, used for Agent Tests, then **deleted** (204; a GET returns 404). The test `spike-39-test` was **deleted** (204); the workspace test list is empty again. Only `Farm record line (draft)` remains.
- Vercel probe project `spike39-bgtasks-probe`: **deleted** with its deployment (absent from `vercel project ls`).
- The draft agent was used read-only (GET, plus one text-only conversation, `conv_7901m42cyshjej6vwnezf9zmg9dc`, about 0.03 USD). The production agent config, the Twilio number and the production Vercel project were not changed.
