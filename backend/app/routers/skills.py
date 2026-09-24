import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.skill_manager import skill_manager

logger = logging.getLogger("app.routers.skills")

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillSummary(BaseModel):
    id: str
    name: str
    title: str
    description: str
    category: str
    format: str
    is_system: bool
    updated_at: str


class SkillDetail(SkillSummary):
    content: str


class CreateSkillRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=5, max_length=500)
    category: str = Field(default="custom")
    format: str = Field(default="pdf")
    content: str = Field(..., min_length=10)


class UpdateSkillRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    format: Optional[str] = None
    content: Optional[str] = None


@router.get("", response_model=List[SkillSummary])
async def list_skills(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Retrieve list of all active skills (system, templates, and user-defined)."""
    del current_user
    skills = skill_manager.list_skills(category=category)
    return skills


@router.get("/{skill_id:path}", response_model=SkillDetail)
async def get_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve full skill specification, guidelines, and code templates."""
    del current_user
    skill = skill_manager.get_skill(skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' not found",
        )
    return skill


@router.post("", response_model=SkillDetail, status_code=status.HTTP_201_CREATED)
async def create_skill(
    body: CreateSkillRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new custom user skill."""
    del current_user
    try:
        new_skill = skill_manager.create_custom_skill(
            name=body.name,
            title=body.title,
            description=body.description,
            category=body.category,
            doc_format=body.format,
            content=body.content,
        )
        return new_skill
    except Exception as e:
        logger.error(f"Error creating custom skill: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create skill: {str(e)}",
        )


@router.put("/{skill_id:path}", response_model=SkillDetail)
async def update_skill(
    skill_id: str,
    body: UpdateSkillRequest,
    current_user: User = Depends(get_current_user),
):
    """Update an existing custom user skill."""
    del current_user
    updated = skill_manager.update_custom_skill(
        skill_id=skill_id,
        title=body.title,
        description=body.description,
        category=body.category,
        doc_format=body.format,
        content=body.content,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system skills or skill does not exist.",
        )
    return updated


@router.delete("/{skill_id:path}", status_code=status.HTTP_200_OK)
async def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a custom user skill."""
    del current_user
    success = skill_manager.delete_custom_skill(skill_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system skill or skill does not exist.",
        )
    return {"message": f"Skill '{skill_id}' deleted successfully"}
