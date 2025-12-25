"""
AI Service for handling LLM interactions with BYOK (Bring Your Own Key) support.
Follows Single Responsibility Principle - handles only AI-related operations.
"""
from typing import List, Dict, Any, Optional

from ..core.config import settings
from ..utils.debug import print_step
from .llm_factory import create_llm_provider, LLMProvider


class AIService:
    """
    Service for handling all AI-related operations including CV generation,
    evaluation, and data transformation.
    
    Supports BYOK: provider and api_key can be passed per-request.
    """
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize the AI service with a specific LLM provider.
        
        Args:
            provider: LLM provider ('openai' or 'gemini')
            api_key: Optional API key (if None, uses system OPENAI_API_KEY for OpenAI)
        """
        self.provider = provider
        self.api_key = api_key
        self._llm_client: Optional[LLMProvider] = None
    
    def _get_llm_client(self) -> LLMProvider:
        """Lazy-initialize LLM client."""
        if self._llm_client is None:
            self._llm_client = create_llm_provider(
                provider=self.provider,
                api_key=self.api_key
            )
        return self._llm_client
    
    async def generate_cv_from_text(self, job_description: str, user_experience: str) -> str:
        """
        Generate a tailored CV based on job description and user experience.
        
        Args:
            job_description: The job description to tailor the CV for
            user_experience: The user's experience and background
            
        Returns:
            Generated CV content
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = "You are a professional CV writer. Generate tailored CVs based on job descriptions."
            user_prompt = f"""
            Based on the following job description and user experience, generate a tailored CV:
            
            Job Description:
            {job_description}
            
            User Experience:
            {user_experience}
            
            Please generate a professional CV that highlights relevant skills and experience.
            """
            
            return await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
        except Exception as e:
            print(f"Error generating CV: {e}")
            raise Exception(f"Failed to generate CV: {str(e)}")
    
    async def extract_structured_cv_data(self, cv_text: str, job_description: str | None = None) -> Dict[str, Any]:
        """
        Extract structured CV data from text using AI.
        
        Args:
            cv_text: The CV text to extract data from
            job_description: Optional job description for context and target_job extraction
            
        Returns:
            Structured CV data as a dictionary
        """
        try:
            llm = self._get_llm_client()
            system_prompt = "You are an expert at extracting structured data from CVs. You also correct grammar, spelling, and punctuation mistakes in the extracted content while preserving the original meaning and professional tone. Always return valid JSON."
            
            # Build prompt conditionally based on whether job_description is provided
            # Check if job_description exists and is not empty after stripping
            has_job_description = bool(job_description and job_description.strip())
            
            if has_job_description:
                user_prompt = f"""
                Extract structured data from the following CV text and format it as JSON.
                The job description is provided for context to help identify relevant information.
                
                IMPORTANT: While extracting, correct any grammar, spelling, and punctuation mistakes in the CV text.
                Preserve the original meaning and professional tone, but ensure all extracted text fields are grammatically correct.
                Fix common issues like: subject-verb agreement, verb tense consistency, capitalization, punctuation, and spelling errors.
                
                Job Description:
                {job_description}
                
                CV Text:
                {cv_text}
                
                Please extract and return the following information in JSON format:
                {{
                    "personal": {{
                        "name": "Full name",
                        "email": "email@example.com",
                        "phone": "phone number",
                        "location": "city, country",
                        "website": "website URL or empty string",
                        "linkedin": "LinkedIn URL or empty string",
                        "github": "GitHub URL or empty string"
                    }},
                    "professional_summary": "Brief professional summary",
                    "experience": [
                        {{
                            "role": "Job title",
                            "company": "Company name",
                            "startDate": "Start date (e.g., 'Jan 2023', '2023', 'Present')",
                            "endDate": "End date (e.g., 'Dec 2023', 'Present', 'Current')",
                            "location": "Job location",
                            "description": "Job description",
                            "achievements": ["achievement 1", "achievement 2"]
                        }}
                    ],
                    "education": [
                        {{
                            "degree": "Degree name",
                            "institution": "Institution name",
                            "field": "Field of study",
                            "startDate": "Start date (e.g., 'Sep 2020', '2020')",
                            "endDate": "End date (e.g., 'May 2023', '2023', 'Present')",
                            "gpa": "GPA if mentioned or empty string"
                        }}
                    ],
                    "projects": [
                        {{
                            "name": "Project name",
                            "description": "Project description",
                            "tech_stack": ["technology1", "technology2"],
                            "link": "Project URL or empty string",
                            "startDate": "Start date if available or null",
                            "endDate": "End date if available or null"
                        }}
                    ],
                    "skills": {{
                        "technical": ["skill1", "skill2"],
                        "soft": ["skill1", "skill2"],
                        "languages": ["language1", "language2"]
                    }},
                    "licenses_certifications": [
                        {{
                            "name": "Certification name",
                            "issuer": "Issuing organization",
                            "date": "Issue date (e.g., 'Jan 2023', '2023')",
                            "expiry": "Expiry date if applicable or null"
                        }}
                    ],
                    "target_job": {{
                        "title": "Job title from the job description (e.g., 'Senior Software Engineer') or empty string if not found",
                        "company": "Company name from the job description (e.g., 'Google') or empty string if not found"
                    }}
                }}
                
                Important: Extract the target job title and company name from the job description provided above. 
                Look for patterns like "Job Title at Company", "Job Title - Company", "Company - Job Title", etc.
                If the job description doesn't clearly contain a job title or company name, use empty strings.
                """
            else:
                user_prompt = f"""
                Extract structured data from the following CV text and format it as JSON.
                
                IMPORTANT: While extracting, correct any grammar, spelling, and punctuation mistakes in the CV text.
                Preserve the original meaning and professional tone, but ensure all extracted text fields are grammatically correct.
                Fix common issues like: subject-verb agreement, verb tense consistency, capitalization, punctuation, and spelling errors.
                
                CV Text:
                {cv_text}
                
                Please extract and return the following information in JSON format:
                {{
                    "personal": {{
                        "name": "Full name",
                        "email": "email@example.com",
                        "phone": "phone number",
                        "location": "city, country",
                        "website": "website URL or empty string",
                        "linkedin": "LinkedIn URL or empty string",
                        "github": "GitHub URL or empty string"
                    }},
                    "professional_summary": "Brief professional summary",
                    "experience": [
                        {{
                            "role": "Job title",
                            "company": "Company name",
                            "startDate": "Start date (e.g., 'Jan 2023', '2023', 'Present')",
                            "endDate": "End date (e.g., 'Dec 2023', 'Present', 'Current')",
                            "location": "Job location",
                            "description": "Job description",
                            "achievements": ["achievement 1", "achievement 2"]
                        }}
                    ],
                    "education": [
                        {{
                            "degree": "Degree name",
                            "institution": "Institution name",
                            "field": "Field of study",
                            "startDate": "Start date (e.g., 'Sep 2020', '2020')",
                            "endDate": "End date (e.g., 'May 2023', '2023', 'Present')",
                            "gpa": "GPA if mentioned or empty string"
                        }}
                    ],
                    "projects": [
                        {{
                            "name": "Project name",
                            "description": "Project description",
                            "tech_stack": ["technology1", "technology2"],
                            "link": "Project URL or empty string",
                            "startDate": "Start date if available or null",
                            "endDate": "End date if available or null"
                        }}
                    ],
                    "skills": {{
                        "technical": ["skill1", "skill2"],
                        "soft": ["skill1", "skill2"],
                        "languages": ["language1", "language2"]
                    }},
                    "licenses_certifications": [
                        {{
                            "name": "Certification name",
                            "issuer": "Issuing organization",
                            "date": "Issue date (e.g., 'Jan 2023', '2023')",
                            "expiry": "Expiry date if applicable or null"
                        }}
                    ],
                    "target_job": {{
                        "title": "",
                        "company": ""
                    }}
                }}
                """
            
            user_prompt += """
            Important guidelines:
            - Grammar correction: All text fields (descriptions, summaries, achievements, etc.) must be grammatically correct with proper spelling and punctuation
            - Date formatting: Use "Present" or "Current" for ongoing positions/education
            - Date formats: Use formats like "Jan 2023", "2023", "Sep 2020 - May 2023"
            - Year-only dates: If only year is available, use just the year (e.g., "2023")
            - Month-year dates: If month and year are available, use "Jan 2023" format
            - Preserve meaning: Do not change the factual content, only correct grammar and spelling
            
            Return only the JSON object, no additional text.
            """
            
            content = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse the JSON response
            import json
            content = content.strip()
            
            # Remove any markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Error extracting structured CV data: {e}")
            raise Exception(f"Failed to extract CV data: {str(e)}")
    
    async def generate_cv_from_file(self, file_content: str, job_description: str) -> str:
        """
        Generate a tailored CV from uploaded file content.
        
        Args:
            file_content: Content from uploaded file
            job_description: The job description to tailor the CV for
            
        Returns:
            Generated CV content
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = "You are a professional CV writer. Improve and tailor existing CVs based on job descriptions."
            user_prompt = f"""
            Based on the following existing CV content and job description, generate an improved, tailored CV:
            
            Existing CV Content:
            {file_content}
            
            Job Description:
            {job_description}
            
            Please improve and tailor the CV to better match the job requirements.
            """
            
            return await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
        except Exception as e:
            print(f"Error generating CV from file: {e}")
            raise Exception(f"Failed to generate CV from file: {str(e)}")
    
    async def evaluate_cv_with_committee(self, cv_content: str, job_description: str) -> Dict[str, Any]:
        """
        Evaluate CV using committee of AI personas.
        
        Args:
            cv_content: The CV content to evaluate
            job_description: The job description to evaluate against
            
        Returns:
            Evaluation results from multiple personas
        """
        try:
            llm = self._get_llm_client()
            
            personas = [
                {
                    "name": "Technical Recruiter",
                    "prompt": "You are a technical recruiter. Evaluate this CV for technical skills and experience relevant to the job."
                },
                {
                    "name": "HR Manager", 
                    "prompt": "You are an HR manager. Evaluate this CV for cultural fit, communication skills, and overall presentation."
                },
                {
                    "name": "Hiring Manager",
                    "prompt": "You are a hiring manager. Evaluate this CV for role-specific qualifications and potential for success."
                }
            ]
            
            evaluations = {}
            
            for persona in personas:
                user_prompt = f"""
                {persona['prompt']}
                
                Job Description:
                {job_description}
                
                CV Content:
                {cv_content}
                
                Please provide:
                1. Overall score (1-10)
                2. Strengths
                3. Areas for improvement
                4. Recommendation (Hire/Maybe/No)
                """
                
                response = await llm.chat_completion(
                    system_prompt=persona['prompt'],
                    user_prompt=user_prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                
                evaluations[persona['name']] = response
            
            return evaluations
            
        except Exception as e:
            print(f"Error evaluating CV: {e}")
            raise Exception(f"Failed to evaluate CV: {str(e)}")

    async def evaluate_with_persona(self, persona: str, job_description: str, cv_content: str) -> Dict[str, Any]:
        """
        Evaluate CV with a specific persona.
        
        Args:
            persona: The persona to use for evaluation
            job_description: The job description to evaluate against
            cv_content: The CV content to evaluate
            
        Returns:
            Evaluation results from the specific persona
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = f"You are {persona}. Provide detailed, professional CV evaluations."
            user_prompt = f"""
            You are {persona}. Evaluate this CV for the given job description.
            
            Job Description:
            {job_description}
            
            CV Content:
            {cv_content}
            
            Please provide:
            1. Overall score (1-10)
            2. Strengths
            3. Areas for improvement
            4. Recommendation (Hire/Maybe/No)
            
            Return your response in JSON format with the following structure:
            {{
                "score": <number between 1-10>,
                "strengths": "<list of strengths>",
                "improvements": "<list of areas for improvement>",
                "recommendation": "<Hire/Maybe/No>",
                "reasoning": "<brief explanation of your evaluation>"
            }}
            """
            
            content = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            content = content.strip()
            
            # Try to parse JSON response
            try:
                import json
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, return a structured response
                return {
                    "score": 7,  # Default score
                    "strengths": "Evaluation completed",
                    "improvements": "See detailed feedback",
                    "recommendation": "Maybe",
                    "reasoning": content
                }
            
        except Exception as e:
            print(f"Error evaluating CV with persona {persona}: {e}")
            return {
                "score": 0,
                "strengths": "Error in evaluation",
                "improvements": "Unable to evaluate",
                "recommendation": "No",
                "reasoning": f"Error: {str(e)}"
            }

    async def rephrase_cv_section(self, section_content: str, section_type: str, job_description: str) -> str:
        """
        Rephrase a specific CV section to better fit the target job.
        
        Args:
            section_content: The content of the CV section to rephrase
            section_type: The type of section (e.g., 'professional_summary', 'experience', 'project')
            job_description: The job description to tailor the content for
            
        Returns:
            Rephrased section content
        """
        try:
            llm = self._get_llm_client()
            
            # Define section-specific prompts
            section_prompts = {
                'professional_summary': "You are a professional CV writer. Rephrase this professional summary to better align with the target job requirements while maintaining authenticity.",
                'experience': "You are a professional CV writer. Rephrase this work experience description to better highlight relevant skills and achievements for the target job.",
                'project': "You are a professional CV writer. Rephrase this project description to better showcase relevant technical skills and impact for the target job.",
                'education': "You are a professional CV writer. Rephrase this education section to better emphasize relevant coursework, achievements, or projects for the target job.",
                'skills': "You are a professional CV writer. Rephrase and reorganize these skills to better match the target job requirements and highlight the most relevant ones first.",
                'certification': "You are a professional CV writer. Rephrase this certification description to better emphasize its relevance to the target job."
            }
            
            base_prompt = section_prompts.get(section_type, "You are a professional CV writer. Rephrase this CV section to better align with the target job requirements.")
            
            user_prompt = f"""
            {base_prompt}
            
            Job Description:
            {job_description}
            
            Current {section_type.replace('_', ' ').title()} Content:
            {section_content}
            
            Instructions:
            1. Rephrase the content to better match the job requirements
            2. Use action verbs and quantifiable achievements where possible
            3. Highlight relevant technical skills and technologies mentioned in the job description
            4. Maintain professional tone and authenticity
            5. Keep the same length or slightly shorter
            6. Focus on impact and results rather than just responsibilities
            7. Use keywords from the job description naturally
            
            Return only the rephrased content, no additional text or explanations.
            """
            
            response = await llm.chat_completion(
                system_prompt=base_prompt,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Error rephrasing CV section: {e}")
            raise Exception(f"Failed to rephrase CV section: {str(e)}")

    async def recommend_template(self, job_description: str, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend the best CV template format based on job description and CV data.
        
        Args:
            job_description: The job description to analyze
            cv_data: The structured CV data
            
        Returns:
            Template recommendation with explanation
        """
        try:
            llm = self._get_llm_client()
            
            # Extract key information from CV data
            experience_count = len(cv_data.get('experience', []))
            has_linear_career = self._analyze_career_progression(cv_data.get('experience', []))
            has_employment_gaps = self._detect_employment_gaps(cv_data.get('experience', []))
            is_career_changer = self._detect_career_change(cv_data.get('experience', []))
            skills_strength = len(cv_data.get('skills', {}).get('technical', [])) + len(cv_data.get('skills', {}).get('soft', []))
            projects_count = len(cv_data.get('projects', []))
            
            system_prompt = "You are an expert CV consultant with deep knowledge of different CV formats and their optimal use cases. Provide detailed, professional recommendations."
            user_prompt = f"""
            You are an expert CV consultant. Based on the job description and CV data, recommend the best CV template format.
            
            Job Description:
            {job_description}
            
            CV Analysis:
            - Experience entries: {experience_count}
            - Linear career progression: {has_linear_career}
            - Employment gaps detected: {has_employment_gaps}
            - Career change detected: {is_career_changer}
            - Skills strength: {skills_strength} total skills
            - Projects count: {projects_count}
            
            Available CV formats:
            1. REVERSE-CHRONOLOGICAL: Traditional format focusing on work history in reverse chronological order. Best for candidates with solid, linear work history and clear career progression.
            2. FUNCTIONAL: Skills-based format emphasizing abilities over work history. Best for career changers, those with employment gaps, or diverse non-linear career paths.
            3. COMBINATION: Hybrid format combining skills emphasis with chronological work history. Best for experienced professionals who want to showcase specific skills while providing clear work history.
            
            Consider these factors:
            - Job requirements and industry standards
            - Candidate's career history and progression
            - Presence of employment gaps or career changes
            - Strength of technical skills vs work experience
            - Industry expectations (e.g., tech vs traditional corporate)
            
            Return your recommendation in JSON format:
            {{
                "recommended_template": "reverse-chronological|functional|combination",
                "confidence_score": <number between 0-100>,
                "reasoning": "<detailed explanation of why this format is best>",
                "format_explanation": "<brief explanation of what this format emphasizes>",
                "alternatives": [
                    {{
                        "template": "template_name",
                        "reason": "<why this could also work>"
                    }}
                ]
            }}
            """
            
            content = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            content = content.strip()
            
            # Parse JSON response
            import json
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Error recommending template: {e}")
            # Return default recommendation
            return {
                "recommended_template": "combination",
                "confidence_score": 50,
                "reasoning": "Unable to analyze CV data properly. Combination format is recommended as it works well for most candidates.",
                "format_explanation": "Combines skills emphasis with chronological work history for maximum flexibility.",
                "alternatives": [
                    {
                        "template": "reverse-chronological",
                        "reason": "Good for candidates with strong work history"
                    },
                    {
                        "template": "functional",
                        "reason": "Good for career changers or those with employment gaps"
                    }
                ]
            }
    
    def _analyze_career_progression(self, experience: List[Dict[str, Any]]) -> bool:
        """Analyze if the career shows linear progression."""
        if len(experience) < 2:
            return True
        
        # Simple heuristic: check if job titles show progression
        titles = [job.get('role', '').lower() for job in experience]
        
        # Look for progression indicators
        progression_keywords = ['senior', 'lead', 'manager', 'director', 'principal', 'architect']
        junior_keywords = ['junior', 'associate', 'assistant', 'intern', 'trainee']
        
        has_senior_roles = any(keyword in ' '.join(titles) for keyword in progression_keywords)
        has_junior_roles = any(keyword in ' '.join(titles) for keyword in junior_keywords)
        
        return has_senior_roles and has_junior_roles
    
    def _detect_employment_gaps(self, experience: List[Dict[str, Any]]) -> bool:
        """Detect if there are significant employment gaps."""
        if len(experience) < 2:
            return False
        
        # This is a simplified check - in a real implementation, you'd parse dates properly
        # For now, we'll assume gaps exist if there are fewer than expected years of experience
        return len(experience) < 3  # Simplified heuristic
    
    def _detect_career_change(self, experience: List[Dict[str, Any]]) -> bool:
        """Detect if there's been a career change."""
        if len(experience) < 2:
            return False
        
        # Look for different industries or job functions
        companies = [job.get('company', '').lower() for job in experience]
        roles = [job.get('role', '').lower() for job in experience]
        
        # Simple heuristic: if roles are very different, it might be a career change
        role_keywords = set()
        for role in roles:
            if 'developer' in role or 'engineer' in role:
                role_keywords.add('tech')
            elif 'manager' in role or 'director' in role:
                role_keywords.add('management')
            elif 'analyst' in role or 'consultant' in role:
                role_keywords.add('analyst')
            elif 'sales' in role or 'marketing' in role:
                role_keywords.add('business')
        
        return len(role_keywords) > 1
    
    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a simple text completion from a prompt.
        
        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            system_prompt: Optional system prompt (defaults to generic assistant)
            
        Returns:
            Generated text completion
        """
        llm = self._get_llm_client()
        system = system_prompt or "You are a helpful assistant."
        
        return await llm.chat_completion(
            system_prompt=system,
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    async def stream_completion(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ):
        """
        Stream a text completion from a prompt (yields chunks).
        
        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            system_prompt: Optional system prompt (defaults to generic assistant)
            
        Yields:
            Text chunks as they are generated
        """
        llm = self._get_llm_client()
        system = system_prompt or "You are a helpful assistant."
        
        # Use streaming method from LLM provider
        async for chunk in llm.stream_chat_completion(
            system_prompt=system,
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk