import uuid

from pydantic import BaseModel, Field
from agentswarm.agents import BaseAgent
from agentswarm.datamodels.context import Context
import httpx

from agentswarm.datamodels.responses import KeyStoreResponse


class ScraperAgentInput(BaseModel):
    url: str = Field(description="The URL to scrape. It must be a valid URL, starting with 'http' or 'https'")

class ScraperAgent(BaseAgent[ScraperAgentInput, KeyStoreResponse]):
    def id(self) -> str:
        return "scraper"

    def description(self, user_id: str) -> str:
        return "I'm able to scrape the web and obtain the content of a given URL."

    async def execute(self, user_id: str, context: Context, input: ScraperAgentInput) -> KeyStoreResponse:
        url = input.url
        if not url.startswith("http") and not url.startswith("https"):
            url = "https://" + url
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        
        if response.status_code in [401, 403, 404, 500]:
            raise Exception(f'Unable to retrieve {url}: error {response.status_code}')
        text = response.text
        key = f"scraper_{uuid.uuid4()}"
        context.store.set(key, text)
        return KeyStoreResponse(key=key, description=f"Scraped information from URL {url}")
