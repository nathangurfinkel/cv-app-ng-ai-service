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
        # Cache for compressed job descriptions: {job_description_hash: (compressed_jd, timestamp)}
        self._jd_cache: Dict[str, tuple[str, float]] = {}
        self._jd_cache_ttl: float = 3600.0  # 1 hour in seconds
        # Cache for compressed job descriptions: {job_description_hash: (compressed_jd, timestamp)}
        self._jd_cache: Dict[str, tuple[str, float]] = {}
        self._jd_cache_ttl: float = 3600.0  # 1 hour in seconds
    
    def _get_llm_client(self) -> LLMProvider:
        """Lazy-initialize LLM client."""
        if self._llm_client is None:
            self._llm_client = create_llm_provider(
                provider=self.provider,
                api_key=self.api_key
            )
        return self._llm_client
    
    def _hash_job_description(self, job_description: str) -> str:
        """Create a hash key for job description caching."""
        import hashlib
        # Use first 200 chars + hash of full text for key (avoid too long keys)
        if len(job_description) > 200:
            key = job_description[:200] + hashlib.md5(job_description.encode()).hexdigest()
        else:
            key = job_description
        return hashlib.md5(key.encode()).hexdigest()
    
    async def summarize_job_requirements(self, job_description: str) -> str:
        """
        Extract key requirements from job description (Top 5 Technical + Top 3 Soft Skills).
        Uses caching to avoid redundant API calls.
        
        Args:
            job_description: Full job description text
            
        Returns:
            Compressed requirements list as formatted string
        """
        import time
        
        # Check cache
        cache_key = self._hash_job_description(job_description)
        current_time = time.time()
        
        if cache_key in self._jd_cache:
            compressed_jd, timestamp = self._jd_cache[cache_key]
            if current_time - timestamp < self._jd_cache_ttl:
                return compressed_jd
            # Cache expired, remove it
            del self._jd_cache[cache_key]
        
        # Clean old cache entries (simple cleanup)
        if len(self._jd_cache) > 100:  # Limit cache size
            expired_keys = [
                key for key, (_, ts) in self._jd_cache.items()
                if current_time - ts >= self._jd_cache_ttl
            ]
            for key in expired_keys:
                del self._jd_cache[key]
        
        # Generate compressed JD
        try:
            llm = self._get_llm_client()
            
            system_prompt = "You are a job requirements extractor. Extract only the essential technical and soft skill requirements."
            user_prompt = f"""
            Extract the Top 5 Technical Requirements and Top 3 Soft Skills from this job description.
            Return as a concise formatted list.
            
            Job Description:
            {job_description}
            
            Format your response as:
            Technical Requirements:
            1. [requirement]
            2. [requirement]
            ...
            
            Soft Skills:
            1. [skill]
            2. [skill]
            ...
            
            Return only the formatted list, no additional text.
            """
            
            compressed_jd = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            compressed_jd = compressed_jd.strip()
            
            # Cache the result
            self._jd_cache[cache_key] = (compressed_jd, current_time)
            
            return compressed_jd
            
        except Exception as e:
            print(f"Error summarizing job requirements: {e}")
            # Fallback: return a simple message
            return f"Key requirements from job description (extraction failed: {str(e)})"
    
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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("[AI_SERVICE] Starting structured CV data extraction", extra={
                "cv_text_length": len(cv_text),
                "cv_text_preview": cv_text[:300] + ("..." if len(cv_text) > 300 else ""),
                "has_job_description": bool(job_description),
                "job_description_length": len(job_description) if job_description else 0,
                "timestamp": __import__("datetime").datetime.now().isoformat()
            })
            
            llm = self._get_llm_client()
            system_prompt = "You are an expert at extracting structured data from CVs. You also correct grammar, spelling, and punctuation mistakes in the extracted content while preserving the original meaning and professional tone. Always return valid JSON."
            
            # Build prompt conditionally based on whether job_description is provided
            # Check if job_description exists and is not empty after stripping
            has_job_description = bool(job_description and job_description.strip())
            
            logger.info("[AI_SERVICE] Calling LLM for extraction", extra={
                "has_job_description": has_job_description,
                "prompt_length": len(system_prompt) + len(cv_text) + (len(job_description) if job_description else 0)
            })
            
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
                
                EXTRACTION GUIDELINES:
                1. Experience achievements: Extract ALL bullet points, list items, or achievements for each job. 
                   If the CV uses bullet points (•, -, *, etc.) or numbered lists, extract each one as a separate item in the achievements array.
                   Do not combine multiple bullet points into a single achievement. Preserve all details from the original CV.
                2. Education degree: If the CV says "B.Sc. in Computer Science", extract:
                   - degree: "B.Sc." (just the degree type/level)
                   - field: "Computer Science" (the field of study)
                   Do NOT put "B.Sc. in Computer Science" in the degree field to avoid duplication.
                3. Phone numbers: Preserve all digits exactly as written, including country codes and formatting characters.
                4. Optional fields (website, linkedin, github): Use empty string "" if not provided in the CV, do NOT make up values.
                5. Target job: Extract the target job title and company name from the job description provided above. 
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
                
                EXTRACTION GUIDELINES:
                1. Experience achievements: Extract ALL bullet points, list items, or achievements for each job. 
                   If the CV uses bullet points (•, -, *, etc.) or numbered lists, extract each one as a separate item in the achievements array.
                   Do not combine multiple bullet points into a single achievement. Preserve all details from the original CV.
                2. Education degree: If the CV says "B.Sc. in Computer Science", extract:
                   - degree: "B.Sc." (just the degree type/level)
                   - field: "Computer Science" (the field of study)
                   Do NOT put "B.Sc. in Computer Science" in the degree field to avoid duplication.
                3. Phone numbers: Preserve all digits exactly as written, including country codes and formatting characters.
                4. Optional fields (website, linkedin, github): Use empty string "" if not provided in the CV, do NOT make up values.
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
            
            logger.info("[AI_SERVICE] Received LLM response", extra={
                "response_length": len(content),
                "response_preview": content[:500] + ("..." if len(content) > 500 else "")
            })
            
            # Parse the JSON response
            import json
            content = content.strip()
            
            # Remove any markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            parsed_data = json.loads(content)
            
            logger.info("[AI_SERVICE] Parsed JSON successfully", extra={
                "has_personal": "personal" in parsed_data,
                "personal_name": parsed_data.get("personal", {}).get("name"),
                "experience_count": len(parsed_data.get("experience", [])),
                "education_count": len(parsed_data.get("education", [])),
                "experience_details": [
                    {
                        "role": exp.get("role"),
                        "company": exp.get("company"),
                        "achievements_count": len(exp.get("achievements", [])),
                        "description_length": len(exp.get("description", "")),
                        "has_description": bool(exp.get("description")),
                        "has_achievements": len(exp.get("achievements", [])) > 0
                    }
                    for exp in parsed_data.get("experience", [])[:3]  # First 3 experiences
                ]
            })
            
            return parsed_data
            
        except Exception as e:
            logger.error("[AI_SERVICE] Error extracting structured CV data", extra={
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)
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

    async def evaluate_with_full_committee(self, job_description: str, cv_content: str) -> Dict[str, Any]:
        """
        Evaluate CV using a full committee in a single call (Board Meeting optimization).
        
        Args:
            job_description: The job description to evaluate against
            cv_content: The CV content to evaluate
            
        Returns:
            Committee evaluation results with recruiter, hr, and manager perspectives
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = "You are an expert Hiring Committee representing 3 perspectives: Technical Recruiter, HR Manager, and Hiring Manager."
            user_prompt = f"""
            Analyze this CV against the Job Description from three distinct perspectives.
            
            Job Description:
            {job_description}
            
            CV Content:
            {cv_content}
            
            Output JSON:
            {{
                "recruiter": {{ "score": 1-10, "strengths": [], "improvements": [], "reasoning": "" }},
                "hr": {{ "score": 1-10, "strengths": [], "improvements": [], "reasoning": "" }},
                "manager": {{ "score": 1-10, "strengths": [], "improvements": [], "reasoning": "" }}
            }}
            
            Guidelines:
            - Technical Recruiter: Focus on technical skills, experience relevance, and qualifications
            - HR Manager: Focus on cultural fit, communication skills, and overall presentation
            - Hiring Manager: Focus on role-specific qualifications and potential for success
            
            Return only valid JSON, no additional text.
            """
            
            content = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.7
            )
            
            content = content.strip()
            
            # Remove markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            # Parse JSON response
            try:
                import json
                parsed = json.loads(content)
                
                # Ensure all required keys exist with proper structure
                result = {
                    "recruiter": parsed.get("recruiter", {
                        "score": 7,
                        "strengths": [],
                        "improvements": [],
                        "reasoning": "Evaluation completed"
                    }),
                    "hr": parsed.get("hr", {
                        "score": 7,
                        "strengths": [],
                        "improvements": [],
                        "reasoning": "Evaluation completed"
                    }),
                    "manager": parsed.get("manager", {
                        "score": 7,
                        "strengths": [],
                        "improvements": [],
                        "reasoning": "Evaluation completed"
                    })
                }
                
                # Normalize strengths and improvements to lists if they're strings
                for key in ["recruiter", "hr", "manager"]:
                    if isinstance(result[key].get("strengths"), str):
                        result[key]["strengths"] = [result[key]["strengths"]] if result[key]["strengths"] else []
                    if isinstance(result[key].get("improvements"), str):
                        result[key]["improvements"] = [result[key]["improvements"]] if result[key]["improvements"] else []
                
                return result
            except json.JSONDecodeError as e:
                print(f"Error parsing committee evaluation JSON: {e}")
                print(f"Response content: {content[:200]}")
                # Return default structure on parse error
                default_eval = {
                    "score": 7,
                    "strengths": ["Evaluation completed"],
                    "improvements": ["See detailed feedback"],
                    "reasoning": "JSON parsing failed, using default evaluation"
                }
                return {
                    "recruiter": default_eval.copy(),
                    "hr": default_eval.copy(),
                    "manager": default_eval.copy()
                }
            
        except Exception as e:
            print(f"Error evaluating CV with full committee: {e}")
            error_eval = {
                "score": 0,
                "strengths": ["Error in evaluation"],
                "improvements": ["Unable to evaluate"],
                "reasoning": f"Error: {str(e)}"
            }
            return {
                "recruiter": error_eval.copy(),
                "hr": error_eval.copy(),
                "manager": error_eval.copy()
            }

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

    async def rephrase_cv_section(
        self,
        section_content: str,
        section_type: str,
        job_description: str,
        instruction_type: str = 'default',
        custom_instruction: str | None = None,
    ) -> str:
        """
        Rephrase a specific CV section to better fit the target job.

        Args:
            section_content: The content of the CV section to rephrase
            section_type: The type of section (e.g., 'professional_summary', 'experience', 'project')
            job_description: The job description to tailor the content for
            instruction_type: Type of rephrase instruction ('grammar', 'shorten', 'formal', 'casual', 'expand', 'custom', 'default')
            custom_instruction: When instruction_type is 'custom', this is the user's free-form instruction.

        Returns:
            Rephrased section content
        """
        try:
            llm = self._get_llm_client()

            # Define section-specific prompts with strict technical editor persona (anti-fluff protocol)
            strict_editor_base = """You are a Strict Technical Editor for Senior Engineering Resumes.

Style Guide:
1. Be Direct: Use simple, strong verbs (e.g., "Led", "Built", "Designed"). Avoid flowery metaphors like "Spearheaded", "Steered", "Orchestrated", or "Fostered".
2. No Fluff: Remove adjectives that add no value (e.g., remove "consistent leadership", "robust solutions", "seamless integration").
3. Fact-Based: Focus on *what* was done and the *result*.
4. Brevity: The output should often be shorter than the input.

Bad Example: "Spearheading the recruitment process to foster employee growth."
Good Example: "Hired and mentored 5 engineers."

If the user asks for 'More Formal', interpret that as 'More Precise', not 'More Fancy'."""

            # Add instruction-specific enhancements
            instruction_enhancements = {
                'grammar': "Act as a Proofreader. Fix typos and syntax ONLY. Do not change word choice.",
                'shorten': "Act as a Ruthless Editor. Cut word count by 30%.",
                'expand': "Expand the text with more detail, examples, or impact while staying factual.",
                'formal': "Make the tone professional and precise, but NOT flowery.",
                'casual': "Make the tone more conversational while maintaining professionalism.",
                'custom': "Follow the user's custom instruction precisely.",
                'default': "",  # Use base anti-fluff protocol
            }

            instruction_append = instruction_enhancements.get(instruction_type, "")
            if instruction_append:
                strict_editor_base = f"{strict_editor_base}\n\n{instruction_append}"

            section_prompts = {
                'professional_summary': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this professional summary to better align with the target job requirements while maintaining authenticity. Do not add skills or responsibilities that are not supported by the source text.",
                'experience': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this work experience description to better highlight relevant skills and achievements for the target job. Do not add skills or responsibilities that are not supported by the source text.",
                'project': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this project description to better showcase relevant technical skills and impact for the target job. Do not add skills or responsibilities that are not supported by the source text.",
                'education': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this education section to better emphasize relevant coursework, achievements, or projects for the target job. Do not add skills or responsibilities that are not supported by the source text.",
                'skills': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase and reorganize these skills to better match the target job requirements and highlight the most relevant ones first. Do not add skills that are not in the source text.",
                'certification': f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this certification description to better emphasize its relevance to the target job. Do not add skills or responsibilities that are not supported by the source text."
            }
            
            base_prompt = section_prompts.get(section_type, f"{strict_editor_base}\n\nYour goal is to improve clarity and impact without inventing facts. Rephrase this CV section to better align with the target job requirements. Do not add skills or responsibilities that are not supported by the source text.")
            
            # Use compressed job requirements instead of full job description
            key_requirements = await self.summarize_job_requirements(job_description)
            
            # Build instruction-specific user prompt
            if instruction_type == 'grammar':
                instruction_text = "Fix typos and syntax errors only. Do not change word choice or meaning."
            elif instruction_type == 'shorten':
                instruction_text = "Cut word count by approximately 30% while preserving all essential information."
            elif instruction_type == 'expand':
                instruction_text = "Expand the text with more detail, concrete examples, or quantified impact. Stay factual and do not invent information."
            elif instruction_type == 'custom' and custom_instruction:
                instruction_text = custom_instruction.strip()
            elif instruction_type == 'formal':
                instruction_text = "Make the tone professional and precise, but NOT flowery. Use formal language without corporate buzzwords."
            elif instruction_type == 'casual':
                instruction_text = "Make the tone more conversational while maintaining professionalism and clarity."
            else:  # default
                instruction_text = """1. Rephrase the content to better match the job requirements
            2. Use simple, direct action verbs (Led, Built, Designed, Managed, Created). DO NOT use flowery verbs like "Spearheaded", "Steered", "Orchestrated", "Fostered", "Championed", or "Pioneered"
            3. Remove unnecessary adjectives that add no value (avoid "robust", "seamless", "consistent", "comprehensive" unless they're essential)
            4. Focus on measurable results and quantifiable achievements where possible
            5. Highlight relevant technical skills and technologies mentioned in the job description
            6. Be concise: the output should be the same length or shorter than the input
            7. Focus on facts: what was done and the result, not flowery descriptions
            8. Use keywords from the job description naturally
            9. Remember: "Professional" means "Precise", not "Fancy" """
            
            user_prompt = f"""
            Key Job Requirements:
            {key_requirements}
            
            Current {section_type.replace('_', ' ').title()} Content:
            {section_content}
            
            Instructions:
            {instruction_text}
            
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

    async def inject_keyword(self, section_content: str, section_type: str, keyword: str, job_description: str) -> str:
        """
        Attempt to inject a keyword into a CV section truthfully.
        Returns either rewritten text with keyword, or "REQUIRES_CONTEXT" if keyword cannot be added truthfully.
        
        Args:
            section_content: The content of the CV section
            section_type: The type of section (e.g., 'professional_summary', 'experience', 'project')
            keyword: The keyword to inject
            job_description: The job description for context
            
        Returns:
            Either rewritten text with keyword, or "REQUIRES_CONTEXT" if keyword cannot be added truthfully
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = f"""You are a strict Resume Editor. The user wants to add the keyword "{keyword}".

RULES:
1. Only add the keyword if it fits naturally into an existing achievement (e.g., changing "deployed code" to "deployed code via CI/CD").
2. DO NOT invent new tasks or responsibilities. Do not say they managed a team if they didn't.
3. If the keyword cannot be added truthfully based only on the text provided, return exactly: "REQUIRES_CONTEXT"
4. If you can add it, return only the rewritten text with no explanations."""

            # Use compressed job requirements instead of full job description
            key_requirements = await self.summarize_job_requirements(job_description)
            
            user_prompt = f"""
Key Job Requirements:
{key_requirements}

Current {section_type.replace('_', ' ').title()} Content:
{section_content}

Task: Add the keyword "{keyword}" to this section if it can be truthfully integrated into existing achievements. If the keyword cannot be naturally added based only on the existing text, return exactly "REQUIRES_CONTEXT" (with no other text).

Return only the rewritten text (if keyword can be added) or "REQUIRES_CONTEXT" (if it cannot be added truthfully).
"""
            
            response = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            result = response.strip()
            # Normalize the response - check if it's the special marker
            if result.upper() == "REQUIRES_CONTEXT" or result == "REQUIRES_CONTEXT":
                return "REQUIRES_CONTEXT"
            
            return result
            
        except Exception as e:
            print(f"Error injecting keyword: {e}")
            raise Exception(f"Failed to inject keyword: {str(e)}")

    async def elaborate_with_keyword(self, section_content: str, section_type: str, keyword: str, user_context: str, job_description: str) -> str:
        """
        Elaborate a CV section with a keyword using user-provided context.
        
        Args:
            section_content: The content of the CV section
            section_type: The type of section (e.g., 'professional_summary', 'experience', 'project')
            keyword: The keyword to add
            user_context: User-provided context about how they used the keyword
            job_description: The job description for context
            
        Returns:
            Rewritten section content with keyword integrated using user context
        """
        try:
            llm = self._get_llm_client()
            
            system_prompt = "You are a Strict Resume Editor. Your task is to rewrite resume content using only the user-provided context as factual basis. Do not invent details beyond what the user explicitly states. Incorporate keywords naturally while maintaining authenticity and professional tone."
            
            # Use compressed job requirements instead of full job description
            key_requirements = await self.summarize_job_requirements(job_description)
            
            user_prompt = f"""
User wants to add "{keyword}" to their resume.
User Context: "{user_context}"

Key Job Requirements:
{key_requirements}

Current {section_type.replace('_', ' ').title()} Content:
{section_content}

Task: Rewrite the Current Text to incorporate the Keyword, using the User Context as the factual basis. Do not invent any details beyond what the user explicitly stated. Enhance the professional tone. Keep it concise. Use action verbs and quantifiable achievements where possible.

Return only the rewritten content, no additional text or explanations.
"""
            
            response = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.7
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Error elaborating with keyword: {e}")
            raise Exception(f"Failed to elaborate with keyword: {str(e)}")

    async def generate_slight_improvement(
        self, 
        current_description: str,
        current_achievements: list[str],
        user_responses: list[str],
        improvements_feedback: list[str],
        job_description: str,
        target_section: str = "experience",
        user_chosen_type: str | None = None
    ) -> Dict[str, Any]:
        """
        Generate a minimal, targeted improvement (either a bullet point or sentence extension).
        
        Args:
            current_description: Current description text
            current_achievements: Current achievement bullets
            user_responses: User's answers to improvement questions
            improvements_feedback: Feedback suggestions from persona evaluation
            job_description: The job description for context
            target_section: The section being improved
            user_chosen_type: User's explicit choice of "bullet" or "sentence" (optional)
            
        Returns:
            Dict with structured improvement: { type: "bullet" | "sentence", content: string }
        """
        try:
            llm = self._get_llm_client()
            
            # Adjust prompt based on user's choice
            if user_chosen_type == "bullet":
                type_instruction = "Generate ONE new bullet point for the achievements section."
                format_instruction = 'Return ONLY valid JSON: {"type": "bullet", "content": "..."}'
            elif user_chosen_type == "sentence":
                type_instruction = "Generate ONE sentence to extend the job description."
                format_instruction = 'Return ONLY valid JSON: {"type": "sentence", "content": "..."}'
            else:
                type_instruction = """Generate either:
1. ONE new bullet point for the achievements section, OR
2. ONE sentence to extend the description"""
                format_instruction = 'Return ONLY valid JSON in this exact format: {"type": "bullet", "content": "..."} or {"type": "sentence", "content": "..."}'
            
            system_prompt = f"""You are a Resume Improvement Assistant. Your task is to generate MINIMAL, targeted improvements.
{type_instruction}

Do not rewrite the entire section. Only add one small improvement that incorporates the user's experience.
{format_instruction}"""
            
            # Use compressed job requirements instead of full job description
            key_requirements = await self.summarize_job_requirements(job_description)
            
            # Format current content
            current_content_display = f"""Current Description:
{current_description if current_description else "(empty)"}

Current Achievements:
{chr(10).join(f"- {a}" for a in current_achievements) if current_achievements else "(none)"}"""
            
            user_context = "\n".join(f"{i+1}. {resp}" for i, resp in enumerate(user_responses) if resp.strip())
            feedback_context = "\n".join(f"- {imp}" for imp in improvements_feedback)
            
            user_prompt = f"""
Feedback from Evaluation:
{feedback_context}

Key Job Requirements:
{key_requirements}

{current_content_display}

User's Additional Experience/Context:
{user_context}

Task: Based on the user's responses and feedback, generate ONE minimal improvement{f' as a {user_chosen_type}' if user_chosen_type else ''}:
{'' if user_chosen_type else '- If the user described a relevant achievement or accomplishment, generate a bullet point'}
{'' if user_chosen_type else '- If the user provided context that extends their role description, generate a sentence extension'}
{'' if user_chosen_type else ''}
Guidelines:
- Keep it concise (1 sentence for sentence extensions, 1 bullet for achievements)
- Use action verbs and quantifiable results where possible
- Only include facts from the user's responses
- Match the professional tone of existing content
{'' if user_chosen_type else '- If current achievements exist and the user described accomplishments, prefer a bullet'}
{'' if user_chosen_type else '- If no achievements exist or user described responsibilities, prefer a sentence'}

{format_instruction}
Do not include any other text or explanations."""
            
            response = await llm.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=200,
                temperature=0.7
            )
            
            # Parse JSON response
            import json
            response_cleaned = response.strip()
            
            # Try to extract JSON if response has extra text
            if not response_cleaned.startswith('{'):
                start_idx = response_cleaned.find('{')
                end_idx = response_cleaned.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    response_cleaned = response_cleaned[start_idx:end_idx+1]
            
            result = json.loads(response_cleaned)
            
            # Validate structure
            if 'type' not in result or 'content' not in result:
                raise ValueError("Invalid JSON structure from LLM")
            
            if result['type'] not in ['bullet', 'sentence']:
                raise ValueError(f"Invalid type: {result['type']}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from LLM: {e}, response: {response}")
            # Fallback: try to extract content and guess type
            content = response.strip().strip('"\'')
            improvement_type = 'bullet' if len(current_achievements) > 0 else 'sentence'
            return {"type": improvement_type, "content": content}
        except Exception as e:
            print(f"Error generating slight improvement: {e}")
            raise Exception(f"Failed to generate slight improvement: {str(e)}")

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