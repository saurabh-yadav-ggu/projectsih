import base64
import mimetypes
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from app.config import settings


def encode_image(image_path: str) -> tuple[str, str]:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/png"

    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    return encoded_string, mime_type


def analyze_image(image_path: str, question: str = "Describe this image in detail.") -> str:
    """Analyze an image file using Ollama vision model."""
    try:
        base64_data, mime_type = encode_image(image_path)

        llm = ChatOllama(
            model=settings.VISION_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": question},
                {
                    "type": "image_url",
                    "image_url": f"data:{mime_type};base64,{base64_data}",
                },
            ]
        )

        response = llm.invoke([message])
        return response.content
    except Exception as e:
        return f"Error executing vision analysis: {str(e)}"
