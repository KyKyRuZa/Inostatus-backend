import hashlib
import hmac
import json
import time
import base64
from app.config import settings


CAPTCHA_TTL_SECONDS = 300


def _get_secret_key() -> bytes:
    return settings.SECRET_KEY.encode("utf-8")


def generate_captcha_challenge() -> dict:
    import random

    operations = ['+', '-']
    op = random.choice(operations)

    if op == '+':
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        answer = a + b
    else:
        a = random.randint(5, 15)
        b = random.randint(1, 5)
        answer = a - b

    challenge = f"{a} {op} {b}"

    payload = {
        "answer": answer,
        "exp": int(time.time()) + CAPTCHA_TTL_SECONDS,
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(_get_secret_key(), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()

    token = base64.urlsafe_b64encode(f"{payload_json}.{signature}".encode("utf-8")).decode("utf-8")

    return {
        "challenge": challenge,
        "token": token,
    }


def verify_captcha_answer(token: str, user_answer: int) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload_json, signature = decoded.rsplit(".", 1)

        expected_signature = hmac.new(
            _get_secret_key(), payload_json.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload = json.loads(payload_json)

        if int(time.time()) > payload.get("exp", 0):
            return False

        return payload.get("answer") == user_answer

    except Exception:
        return False
