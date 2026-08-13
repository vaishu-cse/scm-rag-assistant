import os
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.foundry_service import FoundryService


router = APIRouter(prefix="/api/documents", tags=["Documents"])


foundry_service = FoundryService(
    endpoint=os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
    agent_name=os.getenv("FOUNDRY_AGENT_NAME"),
)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required",
        )

    if not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="Only .md files are allowed",
        )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        # Temporary local file
        with tempfile.NamedTemporaryFile(
            suffix=".md",
            delete=False,
        ) as temp_file:

            temp_file.write(content)
            temp_path = temp_file.name

        try:
            result = foundry_service.upload_document(temp_path)

            return {
                "message": "Document uploaded successfully",
                "filename": file.filename,
                **result,
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )