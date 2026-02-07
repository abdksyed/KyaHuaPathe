import os
import re
from typing import Any, Callable

import logfire
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types

from src.llm_models import LLMModels
from src.prompts.prompt_manager import PromptManager
from src.tools import get_url_context, google_maps, google_search

logfire.configure()

GEMINI_3_PRO = Gemini(
    model=LLMModels.GEMINI_3_PRO,
    retry_options=types.HttpRetryOptions(
        attempts=5,
        initial_delay=1,
        max_delay=10,
        http_status_codes=[403, 408, 429, 500, 502, 503, 504],
    ),
)


class AgentService:
    def __init__(self):
        self.app_name = "KyaHuaPathe"
        db_url = (
            f"postgresql+psycopg://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
            f"@{os.environ['DB_CONTAINER_NAME']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
        )
        self.session_service = DatabaseSessionService(db_url=db_url)
        prompt_manager = PromptManager()
        # Configure generate content with extended timeout
        generate_config = types.GenerateContentConfig(
            http_options=types.HttpOptions(
                timeout=300_000,  # 300 seconds in milliseconds
            ),
        )
        self.grounding_agent = LlmAgent(
            name="ElFacto",
            model=GEMINI_3_PRO,
            static_instruction=prompt_manager("el_facto"),
            tools=[google_search, google_maps, get_url_context],
            generate_content_config=generate_config,
        )
        self.agent = LlmAgent(
            name="Atom",
            model=GEMINI_3_PRO,
            static_instruction=prompt_manager("atom"),
            sub_agents=[self.grounding_agent],
            generate_content_config=generate_config,
        )
        self.runner = Runner(
            app_name=self.app_name,
            agent=self.agent,
            session_service=self.session_service,
        )

    async def run_query(
        self,
        message: str | types.Content,
        user_id: str,
        session_id: str,
        callback: Callable[..., Any],
    ):
        session = await self.session_service.get_session(
            app_name=self.app_name, user_id=user_id, session_id=session_id
        )
        if not session:
            await self.session_service.create_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )

        if isinstance(message, str):
            parts = []
            # if there is youtube video link, extract the link and add as another part
            # https://www.youtube.com/watch?v=dQw4w9WgXcQ or https://youtu.be/dQw4w9WgXcQ
            youtube_pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
            youtube_match = re.search(youtube_pattern, message)
            if youtube_match:
                youtube_link = youtube_match.group(0)
                youtube_link = (
                    f"https://{youtube_link}"
                    if not youtube_link.startswith("https://")
                    else youtube_link
                )
                parts.append(
                    types.Part(file_data=types.FileData(file_uri=youtube_link))
                )
            parts.append(types.Part(text=message))
            message = types.Content(role="user", parts=parts)
        async for event in self.runner.run_async(
            session_id=session_id, user_id=user_id, new_message=message
        ):
            response = await self.format_event_response(event)
            # telegram response after markdown formatting
            await callback(response)

    async def run_query_with_media(
        self,
        message: str,
        media_list: list[tuple[bytes, str]],
        user_id: str,
        session_id: str,
        callback: Callable[..., Any],
    ):
        parts = []
        for media_bytes, mime_type in media_list:
            if mime_type.startswith("video/"):
                # for video we have send the bytes as Blob and not directly as bytes
                parts.append(
                    types.Part(
                        inline_data=types.Blob(data=media_bytes, mime_type=mime_type)
                    )
                )
            else:
                parts.append(
                    types.Part.from_bytes(
                        data=media_bytes,
                        mime_type=mime_type,
                    )
                )
        # Add the final caption if present
        if message:
            parts.append(types.Part(text=message))

        await self.run_query(
            message=types.Content(role="user", parts=parts),
            user_id=user_id,
            session_id=session_id,
            callback=callback,
        )

    async def format_event_response(self, event: Event):
        response = ""
        if event.content and event.content.parts and event.content.parts[0].text:
            response += event.content.parts[0].text

        function_calls: list[types.FunctionCall] = event.get_function_calls()
        for fn_call in function_calls:
            response += f"**{fn_call.name}**\n"
            for key, value in fn_call.args.items():
                response += f"{key}: {value}\n"
            response += "---\n"

        # Currently we don't want to show response of tools
        function_responses: list[types.FunctionResponse] = (
            event.get_function_responses()
        )
        for fn_response in function_responses:
            response += f"**{fn_response.name or 'No name'}**\n"
            response += (
                (fn_response.response.get("result", "N/A") or "N/A")
                if fn_response.response
                else "N/A"
            )
            response += "\n---\n"

        return response
