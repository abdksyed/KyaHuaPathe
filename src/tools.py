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
        description="For DATE trigger - the exact datetime to send the reminder.",
    )
    cron_parameters: CronParameters = Field(
        default=CronParameters(),
        description="For CRON trigger - calendar schedule (hour, minute, day_of_week, etc.).",
    )
    make_call: MakeCall = Field(
        default=MakeCall(),
        description="Make a call to a number with custom message",
    )


async def create_reminder(
    reminder_options: CreateReminder,
    tool_context: ToolContext,
) -> dict:
    """Create a scheduled reminder for the user.
    Args:
        reminder_options (dict): The reminder options to create a reminder.
            - message: The reminder message to send to the user.
            - trigger_type: Type of trigger - DATE (one-time) or CRON (calendar-based recurring).
            - trigger_time: For DATE trigger - the exact datetime to send the reminder.
            - cron_parameters: For CRON trigger - calendar schedule (hour, minute, day_of_week, etc.).
            - make_call: Make a call to a number with custom message
                - call_to: The number to call.
                - twiml_message: The TwiML message to send to the number.
        tool_context: ADK tool context (automatically injected).
    Returns:
        A dict with status and reminder_id for future reference (e.g., deletion).
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
    """Delete a previously created reminder.
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
    """Make a call to a number.
    Args:
        call_to (str) : The number to call. (Options: HIM or HER)
        twiml_message (str) : The TwiML XML message to send to the number.
    Returns:
        A dict with status indicating success or failure.
    """
    twilio_service = TwilioService.get_instance()
    twilio_service.make_call(call_to, twiml_message)
    return {"status": "success", "message": f"Call made to {call_to}"}
