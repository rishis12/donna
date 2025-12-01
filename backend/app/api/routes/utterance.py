from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas import UtteranceRequest, IntentResponse
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...models.interaction import Interaction
from ...services.llm_service import parse_utterance, transcribe_audio
import uuid

router = APIRouter(prefix="/utterance", tags=["utterance"])

@router.post("/process", response_model=IntentResponse)
async def process_utterance(
    request: UtteranceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await parse_utterance(request.text, request.current_time)
    
    # Save interaction
    interaction = Interaction(
        user_id=user.id,
        user_message=request.text,
        assistant_response=result.get("response", ""),
        intent=result.get("intent"),
        entities=result.get("entities")
    )
    db.add(interaction)
    await db.commit()
    
    action_id = str(uuid.uuid4()) if result.get("requires_confirmation") else None
    
    return IntentResponse(
        intent=result.get("intent", "small_talk"),
        entities=result.get("entities", {}),
        response=result.get("response", "I understood your request."),
        requires_confirmation=result.get("requires_confirmation", False),
        action_id=action_id
    )

@router.post("/voice", response_model=IntentResponse)
async def process_voice(
    audio: UploadFile = File(...),
    current_time: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    audio_data = await audio.read()
    text = await transcribe_audio(audio_data)
    
    result = await parse_utterance(text, current_time)
    
    interaction = Interaction(
        user_id=user.id,
        user_message=text,
        assistant_response=result.get("response", ""),
        intent=result.get("intent"),
        entities=result.get("entities")
    )
    db.add(interaction)
    await db.commit()
    
    action_id = str(uuid.uuid4()) if result.get("requires_confirmation") else None
    
    return IntentResponse(
        intent=result.get("intent", "small_talk"),
        entities=result.get("entities", {}),
        response=result.get("response", "I understood your request."),
        requires_confirmation=result.get("requires_confirmation", False),
        action_id=action_id
    )

