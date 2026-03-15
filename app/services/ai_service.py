import logging
import datetime  # <--- Added missing import
from typing import List

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError
from app.schemas.AI_schema import ResumeData

from app.core.config import settings

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from app.core.exceptions import AISafetyBlockedError, AIParseError, AIRateLimitError, AIServiceError

logger = logging.getLogger(__name__)


class ResumeGrade(BaseModel):
    score: int
    reasoning: str
    missing_skills: List[str]
    is_match: bool


class ResumeJobAnalysis(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    score: float


class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.embedding_model = "gemini-embedding-001"
        self.llm_model = "gemini-2.5-flash-lite"
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

        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
            logger.exception("Unexpected error in embedding generation.")
            raise AIServiceError("Failed to generate embedding.") from e

    async def extract_resume_info(self, file_bytes: bytes) -> ResumeData:
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        current_date = datetime.datetime.now().strftime("%B %Y")

        system_instruction = f"""
        You are an expert Technical Recruiter and Data Extraction AI.
        Your task is to parse the provided resume PDF and extract the information into a strictly structured JSON format.
        
        CRITICAL INSTRUCTIONS:
        1. EXTRACT EXACTLY: Do not invent or hallucinate data. If a field is missing, use null or an empty list[].
        2. DATES: Format dates as 'YYYY-MM' where possible.
        3. EXPERIENCE: For each job, extract title, company, start_date, end_date (use '{current_date}' if currently employed), and a brief description of responsibilities.
        4. SKILLS: Extract a flat array of all tools, languages, and frameworks mentioned.
        5. OTHER INFO: Summarize any certifications, spoken languages, or notable awards here.
        6. monthsOfWorkExperience: Calculate total months of work experience based on the provided job history. If dates are missing, make a best effort to estimate based on any available information, but do not guess wildly.
        7. monthOfTotalExperience: Calculate total months of experience including work and projects if possible, but prioritize accuracy and do not inflate numbers without clear evidence.
        """

        user_prompt = "Analyze this resume and return the extracted data strictly matching the requested JSON schema."

        try:
            response = await self.client.aio.models.generate_content(
                model=self.llm_model,
                contents=[
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type="application/pdf"
                    ),
                    user_prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction, 
                    response_mime_type="application/json",
                    response_schema=ResumeData,            
                    temperature=0.0,                       
                )
            )

            if not response.text:
                raise AISafetyBlockedError(
                    "Resume extraction was blocked by safety filters."
                )

            return ResumeData.model_validate_json(response.text)

        except ValidationError as ve:
            logger.error(f"Schema validation failed for resume extraction. Details: {ve.errors()}")
            raise AIParseError("AI returned invalid resume format.") from ve

        except APIError as api_err:
            logger.error("Gemini API error during resume extraction.", exc_info=True)
            self._handle_api_error(api_err)
            raise

        except AISafetyBlockedError:
            raise

        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
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

        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
            logger.exception("Unexpected error in resume grading.")
            raise AIServiceError("Resume grading failed.") from e

    async def analyze_resume_against_job_post(
        self,
        normalized_resume_json: str,
        job_description: str,
        job_requirements: List[str],
        job_responsibilities: List[str],
    ) -> ResumeJobAnalysis:
        if not normalized_resume_json.strip():
            raise ValueError("Normalized resume JSON cannot be empty.")

        if not job_description.strip():
            raise ValueError("Job description cannot be empty.")

        requirements_text = "\n".join(job_requirements)
        responsibilities_text = "\n".join(job_responsibilities)

        prompt = (
            "You are an ATS (Applicant Tracking System) evaluation assistant.\n"
        "Your task is to analyze how well an applicant’s resume matches a job posting.\n"
        "The system has already calculated numeric similarity scores.\n"
        "You DO NOT calculate scores. Instead, you must generate:\n"
        '- "strengths": reasons why the applicant is a good fit \n'
        '- "weaknesses": reasons why the applicant may not be a good fit\n\n'
        '- "score": a numeric score from 1 to 100(float number) indicating overall fit using the job post information and the applicant resume (higher is better)\n\n'
        "Return STRICT valid JSON only.\n\n"
            f"Job Description:\n{job_description.strip()}\n\n"
            f"Job Requirements:\n{requirements_text}\n\n"
            f"Job Responsibilities:\n{responsibilities_text}\n\n"
            f"Normalized Resume JSON:\n{normalized_resume_json.strip()}"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeJobAnalysis,
                    temperature=0,
                )
            )

            if not response.text:
                raise AISafetyBlockedError(
                    "Resume-vs-job analysis was blocked by safety filters."
                )

            return ResumeJobAnalysis.model_validate_json(response.text)

        except ValidationError as ve:
            logger.error("Schema validation failed for resume-vs-job analysis.")
            raise AIParseError("AI returned invalid analysis format.") from ve

        except APIError as api_err:
            logger.error("Gemini API error during resume-vs-job analysis.", exc_info=True)
            self._handle_api_error(api_err)
            raise

        except AISafetyBlockedError:
            raise

        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
            logger.exception("Unexpected error in resume-vs-job analysis.")
            raise AIServiceError("Resume-vs-job analysis failed.") from e

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