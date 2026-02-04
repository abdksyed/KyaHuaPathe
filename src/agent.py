from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.adk.models import Gemini
# from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions import InMemorySessionService
from google.adk.events import Event
from google.genai import types

from src.tools import google_search, google_maps, get_url_context

class AgentService:
    def __init__(self):
        self.app_name = "KyaHuaPathe"
        self.session_service = InMemorySessionService()
        self.grounding_agent = LlmAgent(
            name="ElFacto",
            model=Gemini(model="gemini-3-pro-preview"),
            static_instruction="You are ElFacto, always using different tools to get the most accurate information.",
            tools=[ google_search, google_maps, get_url_context ]
        )
        self.agent = LlmAgent(
            name="Atom",
            model=Gemini(model="gemini-3-pro-preview"),
            static_instruction="You are atom, my always on personal assistant.",
            sub_agents=[self.grounding_agent]
        )
        self.runner = Runner(
            app_name=self.app_name,
            agent=self.agent,
            session_service=self.session_service,
        )

    async def run_query(self, message, user_id, session_id, callback):
        session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
        
        content = types.Content(role='user', parts=[types.Part(text=message)])
        async for event in self.runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=content
        ):  
            response = event.content.parts[0].text if event.content and event.content.parts and event.content.parts[0].text else ""
            # TODO: Currently we just badly join the text, make it better, if doing function calls
            # maybe we don't show the name, ask the model to generate some text before doing function call.
            response += "\n".join([f"{fn.name}: {fn.args}" for fn in event.get_function_calls()])
            response += "\n".join([str(fn.response) for fn in event.get_function_responses()])
            if response:
                await callback(response)
            
agent_service = AgentService()