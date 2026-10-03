# Twilio line

The webhook Twilio calls when someone dials our demo number (+1 628 272 9173). It greets the caller, asks for their PIN on the keypad and records a recap of their day (#14). When the recording is ready, it downloads the WAV, keeps it in `recordings/` and sends it with the PIN to the laptop's `POST /calls` (#15).

Call flow: greeting → "enter your PIN, then press #" → beep → recap (up to 2 minutes, # to finish) → goodbye. A wrong or empty PIN gets one retry, then the call ends. On the free trial, Twilio first plays its trial notice and waits for any key.

## Run it

From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r twilio_line/requirements.txt
set -a; source .env; set +a          # TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PUBLIC_BASE_URL, CALLS_API_URL
.venv/bin/uvicorn twilio_line.app:app --port 8000
ngrok http 8000                      # in a second terminal
```

Put ngrok's `https://…` URL in `PUBLIC_BASE_URL` in `.env` and restart uvicorn: Twilio signs every request with that URL, and the service rejects requests whose signature doesn't match (403). Then point the number's voice webhook at `<ngrok URL>/twilio/voice` (POST); #16 covers that.

## Test it

```bash
.venv/bin/python -m pytest twilio_line
```

## Routes

| Route | Twilio calls it when |
|---|---|
| `POST /twilio/voice` | a call comes in |
| `POST /twilio/pin?attempt=N` | the caller finished typing the PIN (or didn't type one) |
| `POST /twilio/recorded` | the recap recording ended |
| `POST /twilio/recording` | the recording file is ready: download it, then send it to `CALLS_API_URL` (#15) |

PINs stay on the server, keyed by Twilio's `CallSid`, and never go into URLs (`pin_for_call(call_sid)`).

## What `/calls` receives

`POST CALLS_API_URL` as multipart: `audio` (the WAV from Twilio: 8 kHz mono) and `pin` (the digits the caller typed). If `/calls` is down or rejects it (for example 404 for an unknown PIN), the error is logged with the CallSid and the WAV stays in `recordings/<CallSid>.wav`, so it can be sent again.
