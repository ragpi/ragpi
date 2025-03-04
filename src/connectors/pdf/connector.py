import io
import logging
from typing import AsyncGenerator

import aiohttp
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.pdf.config import PdfConfig
from src.connectors.pdf.chunker import chunk_pdf_page  


logger = logging.getLogger(__name__)


class PdfConnector(BaseConnector):
    config: PdfConfig

    def __init__(self, settings: Settings, config: PdfConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        logger.info(f"Extracting PDF from URL: {self.config.pdf_url}")
        try:
            async with aiohttp.ClientSession(
                headers={"User-Agent": self.settings.USER_AGENT}
            ) as session:
                async with session.get(str(self.config.pdf_url)) as response:
                    response.raise_for_status()
                    pdf_content = await response.read()

            with io.BytesIO(pdf_content) as f:
                pdf_reader = PdfReader(f)
                num_pages = len(pdf_reader.pages)

                for page_number, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    page_title = f"Page {page_number + 1} of {num_pages}"

                    chunks = chunk_pdf_page(
                        page_text=text,
                        url=str(self.config.pdf_url),
                        page_title=page_title,
                        chunk_size=self.settings.CHUNK_SIZE,
                        chunk_overlap=self.settings.CHUNK_OVERLAP,
                    )

                    for chunk in chunks:
                        yield chunk 


        except aiohttp.ClientError as e:
            logger.error(f"Error downloading PDF: {e}")
            raise
        except PdfReadError as e:  
            logger.error(f"Error reading PDF: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error extracting PDF: {e}")
            raise