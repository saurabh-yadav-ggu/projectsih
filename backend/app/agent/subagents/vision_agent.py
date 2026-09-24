import logging
from typing import Dict, Any
from app.vision import analyze_image

logger = logging.getLogger("app.agent.subagents.vision")


async def run_vision_agent(
    image_path: str,
    question: str = "Describe this image in detail.",
) -> Dict[str, Any]:
    """
    Vision Agent executing local Ollama multimodal visual analysis.
    """
    try:
        analysis = analyze_image(image_path=image_path, question=question)
        return {
            "agent": "vision_agent",
            "success": True,
            "response": analysis,
            "image_path": image_path,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Vision agent error: {e}")
        return {
            "agent": "vision_agent",
            "success": False,
            "response": f"Failed to analyze image: {str(e)}",
            "image_path": image_path,
            "error": str(e),
        }
