import base64
from unittest.mock import call
import pytest
from typing import Any
from pytest_mock import MockerFixture

from src.connectors.exceptions import ConnectorException
from src.connectors.common.github_client import GitHubClient
from src.connectors.github_pdf.fetcher import GitHubPdfFetcher
from src.connectors.github_pdf.schemas import PdfDocument


# Simple PDF with "Hello PDF" text
SAMPLE_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog /Pages 2 0 R >>\n"
    b"endobj\n"
    b"2 0 obj\n"
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    b"endobj\n"
    b"3 0 obj\n"
    b"<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\n"
    b"endobj\n"
    b"4 0 obj\n"
    b"<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>\n"
    b"endobj\n"
    b"5 0 obj\n"
    b"<< /Length 44 >>\n"
    b"stream\n"
    b"BT\n"
    b"/F1 12 Tf\n"
    b"100 700 Td\n"
    b"(Hello PDF) Tj\n"
    b"ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n"
    b"0 6\n"
    b"0000000000 65535 f\n"
    b"0000000009 00000 n\n"
    b"0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"0000000214 00000 n\n"
    b"0000000304 00000 n\n"
    b"trailer\n"
    b"<< /Size 6 /Root 1 0 R >>\n"
    b"startxref\n"
    b"398\n"
    b"%%EOF\n"
)


@pytest.fixture
async def github_pdf_fetcher(
    github_client: GitHubClient,
) -> GitHubPdfFetcher:
    return GitHubPdfFetcher(github_client=github_client)


async def test_fetch_pdfs_success(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    # Mock repository info response
    repo_response = {
        "default_branch": "main"
    }

    # Mock ref response
    ref_response = {
        "object": {
            "sha": "commit123"
        }
    }

    # Mock commit response
    commit_response = {
        "tree": {
            "sha": "tree123"
        }
    }

    # Mock tree response with PDF files
    tree_response = {
        "tree": [
            {
                "path": "docs/schematic.pdf",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob123"
            },
            {
                "path": "README.md",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob456"
            },
            {
                "path": "hardware/datasheet.PDF",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob789"
            }
        ]
    }

    # Mock blob responses for PDFs
    blob_response_1 = {
        "content": base64.b64encode(SAMPLE_PDF_BYTES).decode("utf-8"),
        "encoding": "base64"
    }

    blob_response_2 = {
        "content": base64.b64encode(SAMPLE_PDF_BYTES).decode("utf-8"),
        "encoding": "base64"
    }

    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.side_effect = [
        (repo_response, {}),
        (ref_response, {}),
        (commit_response, {}),
        (tree_response, {}),
        (blob_response_1, {}),
        (blob_response_2, {}),
    ]

    pdf_docs = [
        doc
        async for doc in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(pdf_docs) == 2
    assert all(isinstance(doc, PdfDocument) for doc in pdf_docs)
    assert pdf_docs[0].path == "docs/schematic.pdf"
    assert pdf_docs[0].url == "https://github.com/test/repo/blob/main/docs/schematic.pdf"
    assert "Hello PDF" in pdf_docs[0].content
    assert pdf_docs[1].path == "hardware/datasheet.PDF"


async def test_fetch_pdfs_with_path_filter(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    repo_response = {"default_branch": "main"}
    ref_response = {"object": {"sha": "commit123"}}
    commit_response = {"tree": {"sha": "tree123"}}

    tree_response = {
        "tree": [
            {
                "path": "docs/schematic.pdf",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob123"
            },
            {
                "path": "hardware/datasheet.pdf",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob789"
            }
        ]
    }

    blob_response = {
        "content": base64.b64encode(SAMPLE_PDF_BYTES).decode("utf-8"),
        "encoding": "base64"
    }

    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.side_effect = [
        (repo_response, {}),
        (ref_response, {}),
        (commit_response, {}),
        (tree_response, {}),
        (blob_response, {}),
    ]

    pdf_docs = [
        doc
        async for doc in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="repo",
            path_filter="docs/"
        )
    ]

    # Should only get docs/schematic.pdf, not hardware/datasheet.pdf
    assert len(pdf_docs) == 1
    assert pdf_docs[0].path == "docs/schematic.pdf"


async def test_fetch_pdfs_with_ref(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    ref_response = {"object": {"sha": "commit456"}}
    commit_response = {"tree": {"sha": "tree456"}}
    tree_response = {"tree": []}

    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.side_effect = [
        (ref_response, {}),
        (commit_response, {}),
        (tree_response, {}),
    ]

    pdf_docs = [
        doc
        async for doc in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="repo",
            ref="develop"
        )
    ]

    assert len(pdf_docs) == 0
    # Verify ref parameter was used
    assert mock_request.call_args_list[0] == call(
        "GET", "https://api.github.com/repos/test/repo/git/ref/heads/develop"
    )


async def test_fetch_pdfs_no_pdfs_found(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    repo_response = {"default_branch": "main"}
    ref_response = {"object": {"sha": "commit123"}}
    commit_response = {"tree": {"sha": "tree123"}}

    # Tree with no PDF files
    tree_response = {
        "tree": [
            {
                "path": "README.md",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob123"
            }
        ]
    }

    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.side_effect = [
        (repo_response, {}),
        (ref_response, {}),
        (commit_response, {}),
        (tree_response, {}),
    ]

    pdf_docs = [
        doc
        async for doc in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(pdf_docs) == 0


async def test_fetch_pdfs_repo_not_found(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.return_value = (None, None)

    with pytest.raises(
        ConnectorException,
        match="Failed to fetch repository info",
    ):
        async for _ in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="nonexistent",
        ):
            pass


async def test_fetch_pdfs_invalid_pdf(
    github_pdf_fetcher: GitHubPdfFetcher,
    mocker: MockerFixture,
) -> None:
    repo_response = {"default_branch": "main"}
    ref_response = {"object": {"sha": "commit123"}}
    commit_response = {"tree": {"sha": "tree123"}}

    tree_response = {
        "tree": [
            {
                "path": "corrupt.pdf",
                "type": "blob",
                "url": "https://api.github.com/repos/test/repo/git/blobs/blob123"
            }
        ]
    }

    # Invalid PDF content
    blob_response = {
        "content": base64.b64encode(b"Not a valid PDF").decode("utf-8"),
        "encoding": "base64"
    }

    mock_request = mocker.patch.object(github_pdf_fetcher.client, "request")
    mock_request.side_effect = [
        (repo_response, {}),
        (ref_response, {}),
        (commit_response, {}),
        (tree_response, {}),
        (blob_response, {}),
    ]

    # Should skip invalid PDFs and not yield them
    pdf_docs = [
        doc
        async for doc in github_pdf_fetcher.fetch_pdfs(
            repo_owner="test",
            repo_name="repo",
        )
    ]

    assert len(pdf_docs) == 0
