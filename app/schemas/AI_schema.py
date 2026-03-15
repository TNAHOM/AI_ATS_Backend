from pydantic import BaseModel, Field
from typing import List, Optional

class SocialMediaLinks(BaseModel):
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github: Optional[str] = Field(default=None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(default=None, description="Personal website or portfolio URL")
    other: Optional[List[str]] = Field(default_factory=list, description="Any other relevant links")

class WorkExperience(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = Field(default=None, description="Format: YYYY-MM or 'Present'")
    end_date: Optional[str] = Field(default=None, description="Format: YYYY-MM or 'Present'")
    total_months: Optional[int] = Field(default=None, description="Calculated total months in this role")
    description: List[str] = Field(description="Bullet points of achievements and responsibilities")

class Project(BaseModel):
    name: str
    description: str
    url: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)

class Education(BaseModel):
    institution: str
    degree: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# class DomainExperience(BaseModel):
#     domain: str = Field(description="e.g., Frontend, Backend, DevOps, Data Science, Management")
#     months: int = Field(description="Total calculated months of experience in this specific domain")

class ResumeData(BaseModel):
    name: str
    email: str
    socialMediaLinks: SocialMediaLinks
    workExperience: List[WorkExperience]
    projects: List[Project]
    education: List[Education]
    skillsAndTechnologies: List[str]
    monthsOfWorkExperience: float
    monthOfTotalExperience: float
    otherInfo: Optional[str] = Field(default=None, description="Certifications, languages, hobbies, etc.")