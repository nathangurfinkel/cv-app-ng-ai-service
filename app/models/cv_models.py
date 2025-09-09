"""
CV-specific Pydantic models for templating system.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DateValue(BaseModel):
    """Enhanced date value model for better date handling."""
    year: int
    month: Optional[int] = None  # 1-12, optional for year-only dates
    day: Optional[int] = None    # 1-31, optional for month/year or year-only dates
    isPresent: Optional[bool] = None  # true for "Present" or "Current" dates

class PersonalInfo(BaseModel):
    """Personal information model."""
    name: str = "Your Name"
    email: str = "your.email@example.com"
    phone: str = "+1234567890"
    location: str = "City, State"
    website: str = "your-website.com"
    linkedin: str = "linkedin.com/in/username"
    github: str = "github.com/username"

class Experience(BaseModel):
    """Professional experience model."""
    company: str
    role: str
    startDate: str
    endDate: str
    location: str
    description: str
    achievements: List[str] = []
    # Enhanced date fields for better handling
    startDateValue: Optional[DateValue] = None
    endDateValue: Optional[DateValue] = None

class Education(BaseModel):
    """Education model."""
    institution: str
    degree: str
    field: str
    startDate: str
    endDate: str
    gpa: str = ""
    # Enhanced date fields for better handling
    startDateValue: Optional[DateValue] = None
    endDateValue: Optional[DateValue] = None

class Project(BaseModel):
    """Project model."""
    name: str
    description: str
    tech_stack: List[str] = []
    link: str = ""
    # Optional date fields for projects
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    startDateValue: Optional[DateValue] = None
    endDateValue: Optional[DateValue] = None

class Skills(BaseModel):
    """Skills model."""
    technical: List[str] = []
    soft: List[str] = []
    languages: List[str] = []

class LicenseCertification(BaseModel):
    """License and certification model."""
    name: str
    issuer: str
    date: str
    expiry: Optional[str] = None
    # Enhanced date fields for better handling
    dateValue: Optional[DateValue] = None
    expiryValue: Optional[DateValue] = None

class CVData(BaseModel):
    """Complete CV data model."""
    personal: PersonalInfo
    professional_summary: str = ""
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    skills: Skills
    licenses_certifications: List[LicenseCertification] = []

class PDFRequest(BaseModel):
    """PDF generation request model."""
    templateId: str
    data: CVData

# Date utility functions
def format_date(date_value: DateValue) -> str:
    """Format a DateValue object into a human-readable string."""
    if date_value.isPresent:
        return "Present"
    
    if date_value.day and date_value.month:
        # Full date: "Jan 2023" or "15 Jan 2023"
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month = month_names[date_value.month - 1]
        return f"{date_value.day} {month} {date_value.year}"
    elif date_value.month:
        # Month/Year: "Jan 2023"
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month = month_names[date_value.month - 1]
        return f"{month} {date_value.year}"
    else:
        # Year only: "2023"
        return str(date_value.year)

def parse_date_string(date_string: str) -> Optional[DateValue]:
    """Parse a date string into a DateValue object."""
    import re
    from datetime import datetime
    
    if not date_string or date_string.lower() in ['present', 'current']:
        return DateValue(year=datetime.now().year, isPresent=True)
    
    # Try to parse various date formats
    patterns = [
        (r'^(\d{4})$', lambda m: DateValue(year=int(m.group(1)))),  # Year only: "2023"
        (r'^(\w{3})\s+(\d{4})$', lambda m: DateValue(year=int(m.group(2)), month=_month_name_to_number(m.group(1)))),  # Month Year: "Jan 2023"
        (r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', lambda m: DateValue(year=int(m.group(3)), month=_month_name_to_number(m.group(2)), day=int(m.group(1)))),  # Day Month Year: "15 Jan 2023"
        (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', lambda m: DateValue(year=int(m.group(3)), month=int(m.group(1)), day=int(m.group(2)))),  # MM/DD/YYYY
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', lambda m: DateValue(year=int(m.group(1)), month=int(m.group(2)), day=int(m.group(3)))),  # YYYY-MM-DD
    ]
    
    for pattern, parser in patterns:
        match = re.match(pattern, date_string)
        if match:
            try:
                return parser(match)
            except (ValueError, AttributeError):
                continue
    
    return None

def _month_name_to_number(month_name: str) -> Optional[int]:
    """Convert month name to number (1-12)."""
    month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    try:
        return month_names.index(month_name.lower()) + 1
    except ValueError:
        return None

def create_date_value(year: int, month: Optional[int] = None, day: Optional[int] = None, is_present: Optional[bool] = None) -> DateValue:
    """Create a DateValue object."""
    return DateValue(year=year, month=month, day=day, isPresent=is_present)
