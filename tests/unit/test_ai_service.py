"""
Unit tests for AI Service.
Follows Single Responsibility Principle - tests only AI service functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.ai_service import AIService


class TestAIService:
    """Test class for AI Service following Single Responsibility Principle."""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing."""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            return AIService()

    @pytest.mark.asyncio
    async def test_extract_structured_cv_data_success(self, ai_service):
        """Test successful CV data extraction."""
        # Arrange
        cv_text = "John Doe, Software Engineer, 5 years experience"
        job_description = "Looking for a software engineer"
        
        with patch.object(ai_service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value.choices = [Mock()]
            mock_create.return_value.choices[0].message.content = '{"personal": {"name": "John Doe"}}'
            
            # Act
            result = await ai_service.extract_structured_cv_data(cv_text, job_description)
            
            # Assert
            assert result is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_rephrase_cv_section_success(self, ai_service):
        """Test successful CV section rephrasing."""
        # Arrange
        section_content = "I am a software engineer"
        section_type = "professional_summary"
        job_description = "Looking for a senior developer"
        
        with patch.object(ai_service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value.choices = [Mock()]
            mock_create.return_value.choices[0].message.content = "Experienced software engineer with expertise in modern development practices"
            
            # Act
            result = await ai_service.rephrase_cv_section(section_content, section_type, job_description)
            
            # Assert
            assert "Experienced software engineer" in result
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_template_success(self, ai_service):
        """Test successful template recommendation."""
        # Arrange
        job_description = "Looking for a software engineer"
        cv_data = {"experience": [{"title": "Software Engineer"}]}
        
        with patch.object(ai_service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value.choices = [Mock()]
            mock_create.return_value.choices[0].message.content = '{"recommended_template": "classic", "confidence_score": 0.85}'
            
            # Act
            result = await ai_service.recommend_template(job_description, cv_data)
            
            # Assert
            assert "recommended_template" in result
            assert result["confidence_score"] == 0.85
            mock_create.assert_called_once()


    def test_initialization_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        # Arrange & Act & Assert
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                AIService()

    @pytest.mark.asyncio
    async def test_extract_structured_cv_data_handles_api_error(self, ai_service):
        """Test that API errors are handled gracefully."""
        # Arrange
        cv_text = "Test CV"
        job_description = "Test job"
        
        with patch.object(ai_service.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            # Act & Assert
            with pytest.raises(Exception, match="API Error"):
                await ai_service.extract_structured_cv_data(cv_text, job_description)
