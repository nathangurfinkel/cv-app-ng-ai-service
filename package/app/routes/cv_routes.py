"""
CV-related API routes.
"""
import json
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from ..models.request_models import CVRequest, ExtractCVRequest, RephraseRequest, TemplateRecommendationRequest
from ..services.ai_service import AIService
from ..services.vectorstore_service import VectorstoreService
from ..services.evaluation_service import EvaluationService
from ..services.data_transformation_service import DataTransformationService
# File processing removed - using cloud-native approach
from ..utils.security import validate_uploaded_file, validate_job_description, validate_cv_text
from ..utils.debug import print_step

router = APIRouter(prefix="/cv", tags=["CV"])

# Initialize services
ai_service = AIService()
vectorstore_service = VectorstoreService()
evaluation_service = EvaluationService(ai_service)
data_transformation_service = DataTransformationService()

@router.post("/tailor")
async def tailor_cv(request: CVRequest):
    """
    Tailor a CV based on job description and user CV text.
    """
    # Validate and sanitize inputs
    validated_job_description = validate_job_description(request.job_description)
    validated_cv_text = validate_cv_text(request.user_cv_text)
    
    print_step("CV Tailoring Request", {
        "job_description_length": len(validated_job_description),
        "user_cv_text_length": len(validated_cv_text)
    }, "input")

    # Create documents from CV text
    docs = vectorstore_service.create_documents(validated_cv_text)
    
    # Clear existing documents and add new ones
    vectorstore_service.clear_vectorstore()
    vectorstore_service.add_documents(docs)

    # Retrieve relevant documents
    retrieved_docs = vectorstore_service.retrieve_documents(validated_job_description)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    
    print_step("Document Retrieval", {
        "retrieved_docs_count": len(retrieved_docs),
        "retrieved_context_length": len(retrieved_context),
        "retrieved_context_preview": retrieved_context[:200] + "..." if len(retrieved_context) > 200 else retrieved_context
    }, "output")
    
    try:
        # Generate structured CV data using AI
        raw_ai_data = await ai_service.extract_structured_cv_data(request.user_cv_text, request.job_description)
        
        # Transform raw AI data to structured CVData model with enhanced dates
        cv_data = data_transformation_service.transform_ai_data_to_cv_data(raw_ai_data)
        
        # Convert back to dictionary for API response
        structured_content = data_transformation_service.cv_data_to_dict(cv_data)
        
        # Debug: Show the actual generated content
        print_step("Generated CV Content Preview", {
            "name": structured_content.get("personal", {}).get("name", "NOT_FOUND"),
            "contact_email": structured_content.get("personal", {}).get("email", "NOT_FOUND"),
            "summary_length": len(structured_content.get("professional_summary", "")),
            "experience_count": len(structured_content.get("experience", [])),
            "education_count": len(structured_content.get("education", [])),
            "skills_technical_count": len(structured_content.get("skills", {}).get("technical", [])) if structured_content.get("skills") else 0,
            "has_enhanced_dates": any(
                exp.get("startDateValue") or exp.get("endDateValue") 
                for exp in structured_content.get("experience", [])
            )
        }, "output")

        # Perform evaluation
        evaluation_results = await evaluation_service.evaluate_cv_complete(
            request.job_description,
            json.dumps(structured_content),
            retrieved_docs
        )
        
        # Add evaluation to structured content
        structured_content['analysis'] = evaluation_results
        
        print_step("CV Tailoring Complete", {
            "final_content_keys": list(structured_content.keys()),
            "analysis_present": 'analysis' in structured_content
        }, "output")
        
        return structured_content

    except Exception as e:
        print_step("CV Tailoring Error", str(e), "error")
        raise HTTPException(status_code=500, detail=str(e))

# File processing route removed - using cloud-native approach
# File uploads should be handled by the frontend and passed as text

@router.post("/extract-cv-data")
async def extract_cv_data(request: ExtractCVRequest):
    """
    Extract structured CV data from text using AI.
    """
    print_step("CV Data Extraction Request", {
        "cv_text_length": len(request.cv_text),
        "job_description_length": len(request.job_description)
    }, "input")

    try:
        # Create documents from CV text
        docs = vectorstore_service.create_documents(request.cv_text)
        
        # Clear existing documents and add new ones
        vectorstore_service.clear_vectorstore()
        vectorstore_service.add_documents(docs)

        # Retrieve relevant documents
        retrieved_docs = vectorstore_service.retrieve_documents(request.job_description)
        retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        print_step("Document Retrieval", {
            "retrieved_docs_count": len(retrieved_docs),
            "retrieved_context_length": len(retrieved_context)
        }, "output")
        
        # Generate structured CV data using AI
        raw_ai_data = await ai_service.extract_structured_cv_data(request.cv_text, request.job_description)
        
        # Transform raw AI data to structured CVData model with enhanced dates
        cv_data = data_transformation_service.transform_ai_data_to_cv_data(raw_ai_data)
        
        # Convert back to dictionary for API response
        structured_content = data_transformation_service.cv_data_to_dict(cv_data)
        
        print_step("CV Data Extraction Complete", {
            "extracted_keys": list(structured_content.keys()),
            "name": structured_content.get("personal", {}).get("name", "NOT_FOUND"),
            "experience_count": len(structured_content.get("experience", [])),
            "education_count": len(structured_content.get("education", [])),
            "has_enhanced_dates": any(
                exp.get("startDateValue") or exp.get("endDateValue") 
                for exp in structured_content.get("experience", [])
            )
        }, "output")
        
        return structured_content

    except Exception as e:
        print_step("CV Data Extraction Error", str(e), "error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rephrase-section")
async def rephrase_cv_section(request: RephraseRequest):
    """
    Rephrase a specific CV section to better fit the target job.
    """
    print_step("CV Section Rephrase Request", {
        "section_type": request.section_type,
        "section_content_length": len(request.section_content),
        "job_description_length": len(request.job_description)
    }, "input")

    try:
        # Use AI service to rephrase the section
        rephrased_content = await ai_service.rephrase_cv_section(
            request.section_content,
            request.section_type,
            request.job_description
        )
        
        print_step("CV Section Rephrase Complete", {
            "original_length": len(request.section_content),
            "rephrased_length": len(rephrased_content),
            "section_type": request.section_type
        }, "output")
        
        return {
            "original_content": request.section_content,
            "rephrased_content": rephrased_content,
            "section_type": request.section_type
        }

    except Exception as e:
        print_step("CV Section Rephrase Error", str(e), "error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommend-template")
async def recommend_template(request: TemplateRecommendationRequest):
    """
    Recommend the best CV template format based on job description and CV data.
    """
    print_step("Template Recommendation Request", {
        "job_description_length": len(request.job_description),
        "cv_data_keys": list(request.cv_data.keys()) if request.cv_data else [],
        "experience_count": len(request.cv_data.get('experience', [])) if request.cv_data else 0
    }, "input")

    try:
        # Use AI service to recommend template
        recommendation = await ai_service.recommend_template(
            request.job_description,
            request.cv_data
        )
        
        print_step("Template Recommendation Complete", {
            "recommended_template": recommendation.get("recommended_template"),
            "confidence_score": recommendation.get("confidence_score"),
            "has_alternatives": len(recommendation.get("alternatives", [])) > 0
        }, "output")
        
        return recommendation

    except Exception as e:
        print_step("Template Recommendation Error", str(e), "error")
        raise HTTPException(status_code=500, detail=str(e))
