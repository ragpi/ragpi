import base64
import logging
from typing import AsyncGenerator
from io import BytesIO

from pypdf import PdfReader

from src.connectors.exceptions import ConnectorException
from src.connectors.common.github_client import GitHubClient
from src.connectors.github_pdf.schemas import PdfDocument


logger = logging.getLogger(__name__)


class GitHubPdfFetcher:
    def __init__(
        self,
        *,
        github_client: GitHubClient,
    ):
        self.client = github_client

    async def fetch_pdfs(
        self,
        repo_owner: str,
        repo_name: str,
        ref: str | None = None,
        path_filter: str | None = None,
    ) -> AsyncGenerator[PdfDocument, None]:
        """
        Traverse the entire repository tree and yield all PDF files.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            ref: Optional branch/tag/commit ref (defaults to default branch)
            path_filter: Optional path prefix filter (e.g., "docs/" to only index PDFs in docs folder)
        """
        # Get the tree recursively
        tree_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees"

        # First, get the default branch if ref is not specified
        if not ref:
            repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
            repo_data, _ = await self.client.request("GET", repo_url)
            if not repo_data:
                raise ConnectorException(f"Failed to fetch repository info for {repo_owner}/{repo_name}")
            ref = repo_data.get("default_branch", "main")

        # Get the tree SHA for the ref
        ref_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/ref/heads/{ref}"
        ref_data, _ = await self.client.request("GET", ref_url)
        if not ref_data:
            # Try as a tag or commit
            ref_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{ref}"
            ref_data, _ = await self.client.request("GET", ref_url)
            if not ref_data:
                raise ConnectorException(f"Failed to fetch ref {ref} for {repo_owner}/{repo_name}")
            tree_sha = ref_data["commit"]["tree"]["sha"]
        else:
            commit_sha = ref_data["object"]["sha"]
            commit_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/commits/{commit_sha}"
            commit_data, _ = await self.client.request("GET", commit_url)
            if not commit_data:
                raise ConnectorException(f"Failed to fetch commit {commit_sha}")
            tree_sha = commit_data["tree"]["sha"]

        # Fetch the entire tree recursively
        tree_full_url = f"{tree_url}/{tree_sha}"
        params = {"recursive": "1"}
        tree_data, _ = await self.client.request("GET", tree_full_url, params=params)

        if not tree_data:
            raise ConnectorException(f"Failed to fetch tree for {repo_owner}/{repo_name}")

        tree_items = tree_data.get("tree", [])

        # Filter for PDF files
        pdf_files = [
            item for item in tree_items
            if item["type"] == "blob" and item["path"].lower().endswith(".pdf")
        ]

        # Apply path filter if specified
        if path_filter:
            pdf_files = [
                item for item in pdf_files
                if item["path"].startswith(path_filter)
            ]

        logger.info(f"Found {len(pdf_files)} PDF files in {repo_owner}/{repo_name}")

        # Fetch and process each PDF
        for pdf_file in pdf_files:
            path = pdf_file["path"]
            logger.info(f"Processing PDF: {path}")

            # Use the blobs API to get the file content
            blob_url = pdf_file["url"]
            blob_data, _ = await self.client.request("GET", blob_url)

            if not blob_data:
                logger.warning(f"Failed to fetch blob for {path}, skipping")
                continue

            content_b64 = blob_data.get("content")
            encoding = blob_data.get("encoding")

            if encoding == "base64":
                try:
                    # Decode the base64 content
                    decoded_bytes = base64.b64decode(content_b64)

                    # Extract text from PDF
                    text_content = self._extract_text_from_pdf(decoded_bytes, path)

                    if not text_content or not text_content.strip():
                        logger.warning(f"No text content extracted from {path}, skipping")
                        continue

                    # Create the HTML URL for the PDF
                    html_url = f"https://github.com/{repo_owner}/{repo_name}/blob/{ref}/{path}"

                    pdf_doc = PdfDocument(
                        path=path,
                        url=html_url,
                        content=text_content,
                    )

                    yield pdf_doc

                except Exception as e:
                    logger.error(f"Failed to process PDF {path}: {e}")
                    continue
            else:
                logger.warning(f"Unexpected encoding '{encoding}' for PDF {path}, skipping")
                continue

    def _extract_text_from_pdf(self, pdf_bytes: bytes, path: str) -> str:
        """
        Extract text content from PDF bytes.

        Args:
            pdf_bytes: The PDF file content as bytes
            path: The file path (for logging)

        Returns:
            Extracted text content
        """
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)

            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # Remove NULL bytes and other control characters that cause database issues
                        page_text = page_text.replace('\x00', '').replace('\r', '\n')
                        # Also remove other problematic control characters except newlines and tabs
                        page_text = ''.join(char for char in page_text if char == '\n' or char == '\t' or ord(char) >= 32)
                        if page_text.strip():  # Only add if there's content after cleaning
                            # Add page marker for better context
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num} of {path}: {e}")
                    continue

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Failed to read PDF {path}: {e}")
            raise ConnectorException(f"Failed to extract text from PDF {path}: {e}")
