"""
Evaluation service for CV assessment.
"""
import asyncio
import math
from typing import Dict, Any, List
from ..core.config import settings
from ..utils.debug import print_step

# Lazy import for ragas to avoid uvloop conflict
RAGAS_AVAILABLE = None
_ragas_imported = False

def _lazy_import_ragas():
    """Lazy import ragas only when needed to avoid uvloop conflict."""
    global RAGAS_AVAILABLE, _ragas_imported, evaluate, faithfulness, answer_relevancy, context_precision, context_recall, Dataset
    
    if _ragas_imported:
        return RAGAS_AVAILABLE
    
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset
        RAGAS_AVAILABLE = True
        _ragas_imported = True
        print("INFO: Ragas evaluation framework loaded successfully.")
        return True
    except (ImportError, ValueError) as e:
        # ValueError can occur if nest_asyncio can't patch uvloop
        print(f"WARNING: Ragas not available: {e}")
        RAGAS_AVAILABLE = False
        _ragas_imported = True
        # Create dummy functions to prevent errors
        def evaluate(*args, **kwargs):
            return None
        def faithfulness(*args, **kwargs):
            return None
        def answer_relevancy(*args, **kwargs):
            return None
        def context_precision(*args, **kwargs):
            return None
        def context_recall(*args, **kwargs):
            return None
        class Dataset:
            @staticmethod
            def from_dict(data):
                return None
        return False

class EvaluationService:
    """Service for CV evaluation operations."""
    
    def __init__(self, ai_service):
        """
        Initialize the evaluation service.
        
        Args:
            ai_service: AI service instance
        """
        self.ai_service = ai_service
    
    async def evaluate_cv_with_ragas(self, job_description: str, cv_content: str, retrieved_docs: List) -> Dict[str, float]:
        """
        Evaluate CV using RAGAS metrics.
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            retrieved_docs: Retrieved documents from vectorstore
            
        Returns:
            RAGAS evaluation scores
        """
        # Lazy import ragas to avoid uvloop conflict
        ragas_available = _lazy_import_ragas()
        
        print_step("RAGAS Evaluation Setup", {
            "ragas_available": ragas_available
        }, "input")
        
        if not ragas_available:
            print_step("RAGAS Evaluation", 
                      "RAGAS not available, using default scores", "info")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0
            }
        
        try:
            print_step("RAGAS Dataset Creation", {
                "question_length": len(job_description),
                "contexts_count": len(retrieved_docs),
                "answer_length": len(cv_content)
            }, "input")
            
            # Validate that we have contexts to evaluate
            if not retrieved_docs:
                print_step("RAGAS Dataset Creation", 
                          "No retrieved documents - skipping RAGAS evaluation", "error")
                return {
                    "faithfulness": 0.0,
                    "answer_relevancy": 0.0,
                    "context_precision": 0.0,
                    "context_recall": 0.0
                }
            
            # Ensure ragas is imported
            _lazy_import_ragas()
            from datasets import Dataset
            
            # Create a proper reference answer for context_precision metric
            reference_answer = f"Based on the job description: {job_description}, the CV should highlight relevant skills and experience."
            
            dataset = Dataset.from_dict({
                'question': [job_description],
                'contexts': [doc.page_content for doc in retrieved_docs],
                'answer': [cv_content],
                'ground_truths': [reference_answer]
            })
            print_step("RAGAS Dataset Creation", "Dataset created successfully", "output")
            
            print_step("RAGAS Evaluation Execution", {
                "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            }, "input")
            
            # Import ragas functions inside the method to avoid uvloop conflict
            from ragas import evaluate
            from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
            
            ragas_result = await asyncio.to_thread(
                evaluate, 
                dataset, 
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
            )
            ragas_scores = ragas_result.to_pandas().to_dict('records')[0]
            print_step("RAGAS Evaluation Execution", "Evaluation completed", "output")
            
            # Handle NaN values in RAGAS scores
            print_step("RAGAS Score Processing", ragas_scores, "input")
            for key, value in ragas_scores.items():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    ragas_scores[key] = 0.0
            print_step("RAGAS Score Processing", "NaN values handled", "output")
            
            return ragas_scores
            
        except Exception as e:
            print_step("RAGAS Evaluation", str(e), "error")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0
            }
    
    async def evaluate_cv_with_committee(self, job_description: str, cv_content: str) -> Dict[str, Any]:
        """
        Evaluate CV using committee of personas (optimized: single call instead of 3).
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            
        Returns:
            Committee evaluation results
        """
        print_step("Committee Evaluation Setup", {
            "personas": settings.EVALUATION_PERSONAS,
            "cv_content_length": len(cv_content),
            "optimization": "single_call"
        }, "input")
        
        # Use optimized single-call method
        committee_result = await self.ai_service.evaluate_with_full_committee(job_description, cv_content)
        
        print_step("Committee Evaluation Execution", {
            "method": "evaluate_with_full_committee"
        }, "input")
        
        # Map the committee result to the expected format
        # Map recruiter -> first persona, hr -> second persona, manager -> third persona
        # This maintains compatibility with existing frontend expectations
        persona_mapping = {
            "recruiter": 0,  # Maps to first persona (Creative Recruiter)
            "hr": 1,          # Maps to second persona (could be HR-related)
            "manager": 2      # Maps to third persona (Strict Hiring Manager)
        }
        
        # Convert committee result to list format matching original structure
        committee_evaluations = []
        for persona_name in settings.EVALUATION_PERSONAS:
            # Map persona index to committee role
            # Default mapping: first -> recruiter, second -> hr, third -> manager
            persona_index = settings.EVALUATION_PERSONAS.index(persona_name)
            if persona_index == 0:
                committee_role = "recruiter"
            elif persona_index == 1:
                committee_role = "hr"
            else:
                committee_role = "manager"
            
            # Get the evaluation for this role
            eval_data = committee_result.get(committee_role, {
                "score": 7,
                "strengths": [],
                "improvements": [],
                "reasoning": "Evaluation completed"
            })
            
            # Ensure strengths and improvements are lists
            if isinstance(eval_data.get("strengths"), str):
                eval_data["strengths"] = [eval_data["strengths"]] if eval_data["strengths"] else []
            if isinstance(eval_data.get("improvements"), str):
                eval_data["improvements"] = [eval_data["improvements"]] if eval_data["improvements"] else []
            
            # Add persona name for compatibility
            eval_data["persona"] = persona_name
            committee_evaluations.append(eval_data)
        
        print_step("Committee Evaluation Execution", {
            "completed_evaluations": len(committee_evaluations)
        }, "output")
        
        # Handle potential NaN values in committee scores
        print_step("Committee Score Processing", committee_evaluations, "input")
        scores = []
        for e in committee_evaluations:
            score = e.get('score', 0)
            if isinstance(score, (int, float)) and not (math.isnan(score) or math.isinf(score)):
                scores.append(score)
            else:
                scores.append(0)
        
        committee_analysis = {
            "individual_evaluations": committee_evaluations,
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0
        }
        print_step("Committee Score Processing", committee_analysis, "output")
        
        return committee_analysis
    
    async def evaluate_cv_complete(self, job_description: str, cv_content: str, retrieved_docs: List) -> Dict[str, Any]:
        """
        Perform complete CV evaluation with both RAGAS and committee evaluation.
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            retrieved_docs: Retrieved documents from vectorstore
            
        Returns:
            Complete evaluation results
        """
        # Run RAGAS and committee evaluation in parallel
        ragas_task = self.evaluate_cv_with_ragas(job_description, cv_content, retrieved_docs)
        committee_task = self.evaluate_cv_with_committee(job_description, cv_content)
        
        ragas_scores, committee_analysis = await asyncio.gather(ragas_task, committee_task)
        
        print_step("Final Analysis Assembly", {
            "ragas_scores": ragas_scores,
            "committee_analysis": committee_analysis
        }, "input")
        
        return {
            "ragas_scores": ragas_scores,
            "committee_evaluation": committee_analysis
        }
