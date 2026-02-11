import os

from pydantic import BaseModel, Field
from twilio.rest import Client


class MakeCall(BaseModel):
    call_to: str = Field(default="HER", description="The number to call.")
    twiml_message: str = Field(
        default="", description="The TwiML message to send to the number."
    )


class TwilioService:
    _instance: "TwilioService" | None = None

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.client = Client(self.account_sid, self.auth_token)
        self.directory = {
            "HER": os.getenv("CALL_TO_HER"),
            "HIM": os.getenv("CALL_TO_HIM"),
        }

    @classmethod
    def get_instance(cls) -> "TwilioService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def make_call(self, call_to: str, twiml_message: str):
        self.client.calls.create(
            twiml='<?xml version="1.0" encoding="UTF-8"?>' + twiml_message,
            to=self.directory.get(call_to, call_to),
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
        )
