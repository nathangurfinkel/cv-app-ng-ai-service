"""
CV evaluation API routes.
"""
from fastapi import APIRouter, HTTPException
from ..models.request_models import EvaluationRequest
from ..services.evaluation_service import EvaluationService
from ..services.ai_service import AIService
from ..utils.debug import print_step

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# Initialize services
ai_service = AIService()
evaluation_service = EvaluationService(ai_service)

@router.post("/cv")
async def evaluate_cv(request: EvaluationRequest):
    """
    Perform a committee evaluation on a provided CV JSON against a job description.
    """
    print_step("Committee Evaluation Request", {
        "job_description_length": len(request.job_description),
        "cv_keys": list(request.cv_json.keys())
    }, "input")

    try:
        # Convert the CV JSON object back to a string for the LLM prompt
        import json
        cv_content_str = json.dumps(request.cv_json, indent=2)

        # Perform committee evaluation
        committee_analysis = await evaluation_service.evaluate_cv_with_committee(
            request.job_description,
            cv_content_str
        )
        
        return committee_analysis

    except Exception as e:
        print_step("Committee Evaluation Error", str(e), "error")
        raise HTTPException(status_code=500, detail=f"Error during evaluation: {e}")
