
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.embeddings.fake import FakeEmbeddingProvider
from app.services.ingestion_service import ingest_document

from app.services.background_ingestion import process_document_in_background


router = APIRouter(prefix="/documents", tags=["Documents"])

CHUNK_SIZE = 1024 * 1024  # 1 MB


def safe_filename(filename: str | None) -> str:
    """Convert an uploaded filename into a safe display name."""

    name = (filename or "document.pdf").replace("\\", "/")
    name = name.split("/")[-1].strip()

    if not name or name in {".", ".."}:
        name = "document.pdf"

    if not name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    return name[:255]


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF and register it in the user's organization."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file must have PDF content type.",
        )

    filename = safe_filename(file.filename)

    organization_id = current_user.organization_id
    document_id = uuid.uuid4()

    organization_dir = (
        Path(settings.storage_dir) / str(organization_id)
    )

    storage_path = organization_dir / f"{document_id}.pdf"

    total_bytes = 0
    first_chunk = True

    try:
        organization_dir.mkdir(parents=True, exist_ok=True)

        with storage_path.open("xb") as destination:
            while True:
                content = file.file.read(CHUNK_SIZE)

                if not content:
                    break

                total_bytes += len(content)

                if total_bytes > settings.max_upload_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="PDF exceeds the maximum upload size.",
                    )

                if first_chunk:
                    if not content.startswith(b"%PDF-"):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid PDF file signature.",
                        )

                    first_chunk = False

                destination.write(content)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        document = Document(
            id=document_id,
            organization_id=organization_id,
            uploaded_by=current_user.id,
            filename=filename,
            file_type="application/pdf",
            storage_path=str(storage_path),
            status="pending",
            total_pages=0,
            total_chunks=0,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        background_tasks.add_task(
            process_document_in_background,
            document_id,
            organization_id,
        )

        return {
            "id": str(document.id),
            "filename": document.filename,
            "status": document.status,
            "message": "PDF uploaded successfully.",
        }

    except HTTPException:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise

    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the uploaded document.",
        )

    finally:
        file.file.close()

@router.post("/{document_id}/process")
def process_uploaded_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract PDF text and save embedded document chunks."""

    # Fake embeddings are for local pipeline testing only.
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A production embedding provider is not configured.",
        )

    try:
        return ingest_document(
            db=db,
            document_id=document_id,
            organization_id=current_user.organization_id,
            embedding_provider=FakeEmbeddingProvider(dimensions=16),
        )

    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
