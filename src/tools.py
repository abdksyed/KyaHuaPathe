import asyncio

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from google import genai
from google.adk.tools import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from src.constants import DB_URL
from src.llm_models import LLMModels
from src.tasks import CronParameters, TaskService, TriggerType
from src.twilio import MakeCall, TwilioService

gemini_client = genai.Client()
FALLBACK_RESPONSE = "[NO RESPONSE FROM TOOL]"


# TODO: use adk.tool, apparently then the prompt will take the doc string as description in the function schema


async def google_search(query: str):
    """
    Search the web using Google Search for real-time information.
    Args:
        query (str): The detailed query to search on google
    Returns:
        str: The summary of the search results
    """
    response: types.GenerateContentResponse = await gemini_client.aio.models.generate_content(
        model=LLMModels.GEMINI_3_PRO,
        contents=query,
        config=types.GenerateContentConfig(
            system_instruction="Run 10-15 google search queries to get information and provide comprehensive summary for the query",
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.HIGH
            ),
        ),
    )
    return response.text or FALLBACK_RESPONSE


async def google_maps(query: str):
    """
    Search Google Maps for location, places, and geographic information.
    Args:
        query (str): The detailed query to search on google maps
    Returns:
        str: The summary of the search results
    """
    response: types.GenerateContentResponse = await gemini_client.aio.models.generate_content(
        model=LLMModels.GEMINI_2_5_PRO,  # Google Maps not supported for Gemini 3 models
        contents=query,
        config=types.GenerateContentConfig(
            system_instruction="Run 10-15 google maps queries to get information and provide comprehensive summary for the query",
            tools=[types.Tool(google_maps=types.GoogleMaps())],
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
        ),
    )
    return response.text or FALLBACK_RESPONSE


async def get_url_context(url: str, query: str):
    """
    Extract information from a URL based on a specific query.
    Args:
        url (str): The URL to get information from
        query (str): The information to be extracted from the given URL or other user instructions
    Returns:
        str: The extracted content or user requested contect from the url content.
    """
    response: types.GenerateContentResponse = await gemini_client.aio.models.generate_content(
        model=LLMModels.GEMINI_3_PRO,
        contents=types.Content(
            role="user", parts=[types.Part(text=query), types.Part(text=f"URL: {url}")]
        ),
        config=types.GenerateContentConfig(
            system_instruction="Get all the information from the url and answer the user query based on the url content",
            tools=[types.Tool(url_context=types.UrlContext())],
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.HIGH
            ),
        ),
    )
    return response.text or FALLBACK_RESPONSE


async def generate_and_run_code(query: str):
    """
    Generate and execute Python code to solve computational tasks.
    Args:
        query (str): The query to generate and run code based on
    Returns:
        str: The results from the generated code
    """
    response: types.GenerateContentResponse = (
        await gemini_client.aio.models.generate_content(
            model=LLMModels.GEMINI_3_PRO,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction="Generate and run code based on the query",
                tools=[types.Tool(code_execution=types.ToolCodeExecution())],
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.HIGH
                ),
            ),
        )
    )
    return response.text or FALLBACK_RESPONSE


class CreateReminder(BaseModel):
    message: str = Field(..., description="The reminder message to send to the user.")
    trigger_type: TriggerType = Field(
        ...,
        description="Type of trigger - DATE (one-time) or CRON (calendar-based recurring).",
    )
    trigger_time: str = Field(
        default="",
        description="For DATE trigger - ISO 8601 datetime with timezone (e.g., 2026-02-15T18:00:00+05:30).",
    )
    cron_parameters: CronParameters = Field(
        default=CronParameters(),
        description="For CRON trigger - calendar schedule fields (year, month, day, week, day_of_week, hour, minute, second). Values can be: specific (6), range (mon-fri), list (1,15), or step (*/2).",
    )
    make_call: MakeCall = Field(
        default=MakeCall(),
        description="Optional. Pass this to make a phone call when the reminder fires along with sending a text reminder. Set call_to to HIM or HER and twiml_message to a valid TwiML XML string.",
    )


async def create_reminder(
    reminder_options: CreateReminder,
    tool_context: ToolContext,
) -> dict:
    """Create a scheduled reminder for the user. Always confirm reminder details with the user before creating.

    Use this tool when the user wants to be reminded at a future time, including scheduled calls.
    If the user says "call me at X time" or "call me tomorrow about Y", use THIS tool with make_call — do NOT use make_call directly for future/scheduled calls.

    Trigger type examples:
        - "Remind me tomorrow at 5 PM" → DATE trigger with trigger_time
        - "Every day at 6 AM" → CRON trigger with hour="6", minute="0"
        - "Every Monday at 9 AM" → CRON with day_of_week="mon", hour="9", minute="0"
        - "Every weekday at 8:30 AM" → CRON with day_of_week="mon-fri", hour="8", minute="30"

    For scheduled calls, pass make_call with:
        - call_to: HIM or HER
        - twiml_message: Valid TwiML XML (see make_call docstring for TwiML format)

    Returns reminder_id — always tell the user this ID so they can delete it later.
    """
    try:
        task_service = TaskService.get_instance(DB_URL)
        reminder_id = await task_service.create_task(
            message=reminder_options.message,
            trigger_type=reminder_options.trigger_type,
            chat_id=tool_context.state["chat_id"],
            reply_message_id=tool_context.state["reply_message_id"],
            trigger_time=reminder_options.trigger_time,
            cron_parameters=reminder_options.cron_parameters,
            make_call=reminder_options.make_call,
        )
        return {"status": "success", "reminder_id": reminder_id}
    except (ValueError, ConflictingIdError, KeyError) as e:
        return {"status": "error", "message": str(e)}


async def delete_reminder(reminder_id: str) -> dict:
    """Delete a previously created reminder. To edit a reminder, delete the old one and create a new one.
    Args:
        reminder_id: The ID of the reminder to delete (returned when creating the reminder).
    Returns:
        A dict with status indicating success or failure.
    """
    task_service = TaskService.get_instance(DB_URL)
    try:
        await task_service.delete_task(reminder_id)
        return {"status": "success", "message": f"Reminder {reminder_id} deleted"}
    except JobLookupError as e:
        return {"status": "error", "message": str(e)}


async def list_reminders(tool_context: ToolContext) -> dict:
    """List all active reminders for the current chat.
    Args:
        tool_context: ADK tool context (automatically injected).
    Returns:
        A dict with status and list of reminders with their IDs, messages, next run times, and triggers.
    """
    task_service = TaskService.get_instance(DB_URL)
    reminders = await task_service.list_tasks(chat_id=tool_context.state["chat_id"])
    return {"status": "success", "reminders": reminders}


async def make_call(call_to: str, twiml_message: str):
    """Make an IMMEDIATE phone call right now. Use ONLY when the user wants to call someone instantly
    (e.g., "call him", "call her", "make a call now"). For future/scheduled calls, use create_reminder with make_call parameter instead.

    Args:
        call_to (str): Who to call — HIM or HER.
        twiml_message (str): TwiML XML message (under 4000 chars). Format:
            <Response>
                <Say voice="Polly.Salli-Neural" language="en-US">Your message</Say>
            </Response>

            <Say> attributes: voice (man, woman, Polly.Salli-Neural for English, Google.hi-IN-Chirp3-HD-Leda for Hindi),
                            language (en-US, hi-IN, etc.), loop (default 1, 0 for infinite).
            Use <Pause length="2"/> BETWEEN <Say> tags for pauses.
            For Hindi, ALWAYS use voice="Google.hi-IN-Chirp3-HD-Leda" language="hi-IN".
            For long texts, break into multiple <Say> tags with <Pause> in between.
    Returns:
        A dict with status indicating success or failure.
    """
    try:
        twilio_service = TwilioService.get_instance()
        await asyncio.to_thread(twilio_service.make_call, call_to, twiml_message)
        return {"status": "success", "message": f"Call made to {call_to}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
