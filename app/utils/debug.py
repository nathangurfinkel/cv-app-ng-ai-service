"""
Debug utilities for logging and debugging.
"""
import json
from typing import Any, Optional
from ..core.config import settings

def print_step(step_name: str, data: Optional[Any] = None, data_type: str = "info") -> None:
    """
    Helper function to print formatted debug information.
    
    Args:
        step_name: Name of the step being logged
        data: Data to log (optional)
        data_type: Type of data (input, output, error, info)
    """
    if not settings.DEBUG:
        return
        
    print(f"\n{'='*60}")
    print(f"🔍 STEP: {step_name}")
    print(f"{'='*60}")
    
    if data is not None:
        if data_type == "input":
            print(f"📥 INPUT DATA:")
        elif data_type == "output":
            print(f"📤 OUTPUT DATA:")
        elif data_type == "error":
            print(f"❌ ERROR:")
        else:
            print(f"ℹ️  DATA:")
        
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(str(data))
    
    print(f"{'='*60}\n")
