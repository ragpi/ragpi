import base64
from typing import AsyncGenerator
from src.document_extractor.clients.github import GitHubClient
from src.document_extractor.exceptions import DocumentExtractorException
from src.document_extractor.schemas import MarkdownPage


class GitHubReadmeClient(GitHubClient):
    def __init__(self, *, user_agent: str, github_api_version: str, github_token: str):
        super().__init__(
            concurrent_requests=1,
            user_agent=user_agent,
            github_api_version=github_api_version,
            github_token=github_token,
        )

    async def fetch_readmes(
        self,
        repo_owner: str,
        repo_name: str,
        include_root: bool = True,
        sub_dirs: list[str] | None = None,
        ref: str | None = None,
    ) -> AsyncGenerator[MarkdownPage, None]:
        base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/readme"

        dirs: list[str] = []

        if include_root:
            dirs.append("")

        if sub_dirs:
            dirs.extend(sub_dirs)

        if not dirs:
            raise DocumentExtractorException(
                "No directories specified to fetch READMEs"
            )

        for dir in dirs:
            url = base_url + (f"/{dir}" if dir else "")
            params: dict[str, str] = {}
            if ref:
                params["ref"] = ref

            data, _ = await self.request("GET", url, params=params)
            if not data:
                raise DocumentExtractorException(
                    f"Failed to fetch README content at {url}"
                )

            content_b64 = data["content"]
            encoding = data["encoding"]

            if encoding == "base64":
                try:
                    decoded_bytes = base64.b64decode(content_b64)
                    decoded_str = decoded_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    raise DocumentExtractorException(
                        f"Failed to decode README content at {url}: {e}"
                    )
            else:
                raise DocumentExtractorException(
                    f"Unexpected encoding '{encoding}' for README content at {url}"
                )

            page = MarkdownPage(
                title=data["path"],
                url=data["html_url"],
                content=decoded_str,
            )

            yield page
