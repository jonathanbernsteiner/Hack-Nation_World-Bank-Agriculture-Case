"""Test helpers: post Twilio-style forms signed the way Twilio signs them."""

from twilio.request_validator import RequestValidator

AUTH_TOKEN = "test-auth-token"
PUBLIC_BASE_URL = "https://farm-line.example.ngrok.app"


def post_signed(client, path, form, base_url=PUBLIC_BASE_URL):
    signature = RequestValidator(AUTH_TOKEN).compute_signature(base_url + path, form)
    return client.post(path, data=form, headers={"X-Twilio-Signature": signature})
