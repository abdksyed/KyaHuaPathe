from google import genai
from google.genai import types

async def google_search(query:str):
    response: types.GenerateContentResponse =  await genai.Client().aio.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=query,
                    config=types.GenerateContentConfig(
                        system_instruction="Run 10-15 google search queries to get information and provide comprehensive summary for the query",
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        thinking_config=types.ThinkingConfig(
                            thinking_level=types.ThinkingLevel.HIGH
                        )
                    ),
                )

    return response.text

async def google_maps(query:str):
    response: types.GenerateContentResponse =  await genai.Client().aio.models.generate_content(
                    model="gemini-2.5-pro", # Google Maps not supported for Gemini 3 models
                    contents=query,
                    config=types.GenerateContentConfig(
                        system_instruction="Run 10-15 google maps queries to get information and provide comprehensive summary for the query",
                        tools=[types.Tool(google_maps=types.GoogleMaps())],
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=-1
                        )
                    ),
                )

    return response.text

async def get_url_context(url:str, query:str):
    response: types.GenerateContentResponse =  await genai.Client().aio.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=types.Content(
                        role="user",
                        parts=[
                            types.Part(text=query),
                            types.Part(text=f"URL: {url}")
                        ]
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction="Get all the information from the url and answer the user query based on the url content",
                        tools=[types.Tool(url_context=types.UrlContext())],
                        thinking_config=types.ThinkingConfig(
                            thinking_level=types.ThinkingLevel.HIGH
                        )
                    ),
                )

    return response.text