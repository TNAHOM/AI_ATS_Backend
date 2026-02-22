import logging
from typing import List

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from app.core.config import settings

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from app.core.exceptions import AISafetyBlockedError, AIParseError, AIRateLimitError, AIServiceError

logger = logging.getLogger(__name__)

class ResumeData(BaseModel):
    name: str
    email: str
    skills: List[str]
    experience_years: int
    education: List[str]


class ResumeGrade(BaseModel):
    score: int
    reasoning: str
    missing_skills: List[str]
    is_match: bool


class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.embedding_model = "gemini-embedding-001"
        self.llm_model = "gemini-2.5-flash"
        self.max_attempts = 3

    # Retry only transient API errors
    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(APIError),
        reraise=True
    )
    async def get_embedding(self, text: str, is_query: bool = False) -> List[float]:

        if not text or not text.strip():
            raise ValueError("Text for embedding cannot be empty.")

        try:
            task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"

            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=text.strip(),
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=768
                )
            )

            if not response.embeddings or not response.embeddings[0].values:
                raise AISafetyBlockedError(
                    "Embedding generation was blocked by safety filters."
                )

            return response.embeddings[0].values

        except APIError as api_err:
            logger.error("Gemini API error during embedding.", exc_info=True)
            self._handle_api_error(api_err)
            raise

        except Exception as e:
            logger.exception("Unexpected error in embedding generation.")
            raise AIServiceError("Failed to generate embedding.") from e

    async def extract_resume_info(self, file_bytes: bytes) -> ResumeData:
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        try:
            response = await self.client.aio.models.generate_content(
                model=self.llm_model,
                contents=[
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type="application/pdf"
                    ),
                    "Extract candidate info from this resume. "
                    "Return STRICT valid JSON only."
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeData,
                    temperature=0,
                )
            )

            if not response.text:
                raise AISafetyBlockedError(
                    "Resume extraction was blocked by safety filters."
                )

            return ResumeData.model_validate_json(response.text)

        except ValidationError as ve:
            logger.error("Schema validation failed for resume extraction.")
            raise AIParseError("AI returned invalid resume format.") from ve

        except APIError as api_err:
            logger.error("Gemini API error during resume extraction.", exc_info=True)
            self._handle_api_error(api_err)
            raise

        except AISafetyBlockedError:
            raise

        except Exception as e:
            logger.exception("Unexpected error in resume extraction.")
            raise AIServiceError("Resume extraction failed.") from e

    async def grade_resume(
        self,
        resume_text: str,
        job_description: str
    ) -> ResumeGrade:
        if not resume_text.strip():
            raise ValueError("Resume text cannot be empty.")
        if not job_description.strip():
            raise ValueError("Job description cannot be empty.")

        prompt = (
            "Grade the following resume against the job description.\n\n"
            f"Job Description:\n{job_description.strip()}\n\n"
            f"Resume:\n{resume_text.strip()}\n\n"
            "Return STRICT valid JSON only."
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeGrade,
                    temperature=0,
                )
            )

            if not response.text:
                raise AISafetyBlockedError(
                    "Resume grading was blocked by safety filters."
                )

            return ResumeGrade.model_validate_json(response.text)

        except ValidationError as ve:
            logger.error("Schema validation failed for resume grading.")
            raise AIParseError("AI returned invalid grading format.") from ve

        except APIError as api_err:
            logger.error("Gemini API error during resume grading.", exc_info=True)
            self._handle_api_error(api_err)
            raise

        except AISafetyBlockedError:
            raise

        except Exception as e:
            logger.exception("Unexpected error in resume grading.")
            raise AIServiceError("Resume grading failed.") from e

    # Centralized API Error Handling
    def _handle_api_error(self, api_err: APIError) -> None:
        """
        Normalize API errors into domain-specific exceptions.
        """

        if getattr(api_err, "status_code", None) == 429:
            raise AIRateLimitError("AI quota exceeded.") from api_err

        if getattr(api_err, "status_code", None) in (500, 502, 503, 504):
            # transient server error (retry handled by tenacity)
            return
 
        raise AIServiceError("AI provider error.") from api_err


ai_service = GeminiService()