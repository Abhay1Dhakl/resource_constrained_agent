import os
from io import BytesIO
from typing import Any

from pydantic import BaseModel, Field

from resource_agent.config import load_env_file

MAX_PROFILE_SOURCE_CHARS = 24000


class ProfileSkillBuckets(BaseModel):
    programming: list[str] = Field(default_factory=list)
    ai_ml: list[str] = Field(default_factory=list)
    backend: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class ProfileProject(BaseModel):
    name: str = ""
    description: str = ""
    topics: list[str] = Field(default_factory=list)


class PersonalProfilePayload(BaseModel):
    name: str = ""
    target_role: str = ""
    target_companies: list[str] = Field(default_factory=list)
    skills: ProfileSkillBuckets = Field(default_factory=ProfileSkillBuckets)
    projects: list[ProfileProject] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    interview_focus: list[str] = Field(default_factory=list)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract readable text from a PDF upload.

    Args:
        pdf_bytes: Raw PDF file contents.

    Returns:
        str: Extracted text truncated to a bounded size for profile conversion.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError(
            "The 'pypdf' package is required for PDF uploads. Install the demo dependencies."
        ) from exc

    reader = PdfReader(BytesIO(pdf_bytes))
    extracted_pages = []

    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if page_text:
            extracted_pages.append(page_text)

    combined_text = "\n\n".join(extracted_pages).strip()
    if not combined_text:
        raise ValueError("No readable text could be extracted from the PDF.")

    return combined_text[:MAX_PROFILE_SOURCE_CHARS]


def convert_resume_text_to_profile(
    resume_text: str,
    api_key: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    """Convert resume text into the profile schema expected by the agent.

    Args:
        resume_text: Text extracted from a resume or profile document.
        api_key: Optional OpenAI API key override.
        model: Optional OpenAI model override.
        reasoning_effort: Optional reasoning effort override.

    Returns:
        dict[str, Any]: Profile payload matching the personal profile schema.
    """
    load_env_file()

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    model = model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    reasoning_effort = reasoning_effort or os.getenv("OPENAI_REASONING_EFFORT", "low")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required to convert a PDF into profile JSON.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for PDF-to-profile conversion."
        ) from exc

    client = OpenAI(api_key=api_key)
    instructions = (
        "Convert the resume or profile text into the structured personal profile schema.\n"
        "Rules:\n"
        "1. Return only the structured profile.\n"
        "2. Use empty strings or empty arrays when information is missing.\n"
        "3. Do not invent employers, skills, companies, or project names that are not supported by the text.\n"
        "4. You may infer a likely target_role, interview_focus, and up to 3 weak_areas conservatively when the text strongly suggests them.\n"
        "5. Keep weak_areas concise and practical for interview preparation.\n"
        "6. Put technologies into the most relevant skills bucket.\n"
        "7. Keep project descriptions short and factual.\n"
        "8. Use ASCII only."
    )
    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=(
            "Resume/profile text:\n"
            f"{resume_text}\n\n"
            "Return the structured profile."
        ),
        reasoning={"effort": reasoning_effort},
        text_format=PersonalProfilePayload,
    )

    parsed = response.output_parsed
    if parsed is None:
        raise ValueError("OpenAI returned no structured profile.")

    return parsed.model_dump()
