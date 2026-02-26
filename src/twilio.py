import os

from pydantic import BaseModel, ConfigDict, Field
from twilio.rest import Client


class MakeCall(BaseModel):
    model_config = ConfigDict(
        extra="ignore"
    )  # ignore any additional fields that are not in the model

    call_to: str = Field(default="HER", description="The number to call.")
    twiml_message: str = Field(
        default="", description="The TwiML message to send to the number."
    )


class TwilioService:
    _instance: "TwilioService" | None = None

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        if not self.account_sid or not self.auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
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
