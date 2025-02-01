from typing import AsyncGenerator
from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.chunker import chunk_markdown_page
from src.connectors.common.github_client import GitHubClient
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.github_readme.config import GithubReadmeConfig
from src.connectors.github_readme.fetcher import GitHubReadmeFetcher


class GithubReadmeConnector(BaseConnector):
    config: GithubReadmeConfig

    def __init__(self, settings: Settings, config: GithubReadmeConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        async with GitHubClient(
            concurrent_requests=1,
            user_agent=self.settings.USER_AGENT,
            github_api_version=self.settings.GITHUB_API_VERSION,
            github_token=self.settings.GITHUB_TOKEN,
        ) as github_client:
            readme_fetcher = GitHubReadmeFetcher(github_client=github_client)

            async for page in readme_fetcher.fetch_readmes(
                repo_owner=self.config.repo_owner,
                repo_name=self.config.repo_name,
                include_root=self.config.include_root,
                sub_dirs=self.config.sub_dirs,
            ):
                chunks = chunk_markdown_page(
                    page_data=page,
                    chunk_size=self.settings.CHUNK_SIZE,
                    chunk_overlap=self.settings.CHUNK_OVERLAP,
                )
                for chunk in chunks:
                    yield chunk
