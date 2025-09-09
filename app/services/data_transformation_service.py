"""
Data Transformation Service for converting raw AI extracted data to structured CVData models.
Follows Single Responsibility Principle - handles only data transformation operations.
"""
from typing import Dict, Any, List, Optional
from ..models.cv_models import (
    CVData, PersonalInfo, Experience, Education, Project, 
    Skills, LicenseCertification, DateValue, parse_date_string
)
from ..utils.debug import print_step


class DataTransformationService:
    """
    Service for transforming raw AI extracted data into structured CVData models.
    """
    
    def __init__(self):
        """Initialize the data transformation service."""
        pass
    
    def transform_ai_data_to_cv_data(self, ai_data: Dict[str, Any]) -> CVData:
        """
        Transform raw AI extracted data into structured CVData model.
        
        Args:
            ai_data: Raw data extracted by AI service
            
        Returns:
            Structured CVData model with enhanced date handling
        """
        print_step("Data Transformation", {
            "input_keys": list(ai_data.keys()),
            "has_personal": "personal" in ai_data,
            "has_experience": "experience" in ai_data,
            "has_education": "education" in ai_data
        }, "input")
        
        try:
            # Transform personal information
            personal_data = ai_data.get("personal", {})
            personal = PersonalInfo(
                name=personal_data.get("name", ""),
                email=personal_data.get("email", ""),
                phone=personal_data.get("phone", ""),
                location=personal_data.get("location", ""),
                website=personal_data.get("website", ""),
                linkedin=personal_data.get("linkedin", ""),
                github=personal_data.get("github", "")
            )
            
            # Transform professional summary
            professional_summary = ai_data.get("professional_summary", "")
            
            # Transform experience
            experience_data = ai_data.get("experience", [])
            experience = []
            for exp_data in experience_data:
                exp = Experience(
                    company=exp_data.get("company", ""),
                    role=exp_data.get("role", ""),
                    startDate=exp_data.get("startDate", ""),
                    endDate=exp_data.get("endDate", ""),
                    location=exp_data.get("location", ""),
                    description=exp_data.get("description", ""),
                    achievements=exp_data.get("achievements", []),
                    # Parse and add enhanced date values
                    startDateValue=self._parse_date(exp_data.get("startDate", "")),
                    endDateValue=self._parse_date(exp_data.get("endDate", ""))
                )
                experience.append(exp)
            
            # Transform education
            education_data = ai_data.get("education", [])
            education = []
            for edu_data in education_data:
                edu = Education(
                    institution=edu_data.get("institution", ""),
                    degree=edu_data.get("degree", ""),
                    field=edu_data.get("field", ""),
                    startDate=edu_data.get("startDate", ""),
                    endDate=edu_data.get("endDate", ""),
                    gpa=edu_data.get("gpa", ""),
                    # Parse and add enhanced date values
                    startDateValue=self._parse_date(edu_data.get("startDate", "")),
                    endDateValue=self._parse_date(edu_data.get("endDate", ""))
                )
                education.append(edu)
            
            # Transform projects
            projects_data = ai_data.get("projects", [])
            projects = []
            for proj_data in projects_data:
                proj = Project(
                    name=proj_data.get("name", ""),
                    description=proj_data.get("description", ""),
                    tech_stack=proj_data.get("tech_stack", []),
                    link=proj_data.get("link", ""),
                    # Optional date fields
                    startDate=proj_data.get("startDate"),
                    endDate=proj_data.get("endDate"),
                    startDateValue=self._parse_date(proj_data.get("startDate")) if proj_data.get("startDate") else None,
                    endDateValue=self._parse_date(proj_data.get("endDate")) if proj_data.get("endDate") else None
                )
                projects.append(proj)
            
            # Transform skills
            skills_data = ai_data.get("skills", {})
            skills = Skills(
                technical=skills_data.get("technical", []),
                soft=skills_data.get("soft", []),
                languages=skills_data.get("languages", [])
            )
            
            # Transform licenses and certifications
            certs_data = ai_data.get("licenses_certifications", [])
            licenses_certifications = []
            for cert_data in certs_data:
                cert = LicenseCertification(
                    name=cert_data.get("name", ""),
                    issuer=cert_data.get("issuer", ""),
                    date=cert_data.get("date", ""),
                    expiry=cert_data.get("expiry"),
                    # Parse and add enhanced date values
                    dateValue=self._parse_date(cert_data.get("date", "")),
                    expiryValue=self._parse_date(cert_data.get("expiry")) if cert_data.get("expiry") else None
                )
                licenses_certifications.append(cert)
            
            # Create CVData object
            cv_data = CVData(
                personal=personal,
                professional_summary=professional_summary,
                experience=experience,
                education=education,
                projects=projects,
                skills=skills,
                licenses_certifications=licenses_certifications
            )
            
            print_step("Data Transformation Complete", {
                "personal_name": cv_data.personal.name,
                "experience_count": len(cv_data.experience),
                "education_count": len(cv_data.education),
                "projects_count": len(cv_data.projects),
                "certifications_count": len(cv_data.licenses_certifications),
                "has_enhanced_dates": any(
                    exp.startDateValue or exp.endDateValue for exp in cv_data.experience
                ) or any(
                    edu.startDateValue or edu.endDateValue for edu in cv_data.education
                )
            }, "output")
            
            return cv_data
            
        except Exception as e:
            print_step("Data Transformation Error", str(e), "error")
            raise Exception(f"Failed to transform AI data to CVData: {str(e)}")
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[DateValue]:
        """
        Parse a date string into a DateValue object.
        
        Args:
            date_string: Date string to parse
            
        Returns:
            DateValue object or None if parsing fails
        """
        if not date_string:
            return None
        
        try:
            return parse_date_string(date_string)
        except Exception as e:
            print(f"Warning: Failed to parse date '{date_string}': {e}")
            return None
    
    def cv_data_to_dict(self, cv_data: CVData) -> Dict[str, Any]:
        """
        Convert CVData model back to dictionary format for API responses.
        
        Args:
            cv_data: CVData model to convert
            
        Returns:
            Dictionary representation of CVData
        """
        try:
            return cv_data.model_dump()
        except Exception as e:
            print_step("CVData to Dict Error", str(e), "error")
            raise Exception(f"Failed to convert CVData to dictionary: {str(e)}")


# Global instance
data_transformation_service = DataTransformationService()
