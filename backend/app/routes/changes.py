from fastapi import APIRouter

from app.core.deps import ChangeServiceDep, CsrfDep
from app.schemas.changes import RecentChangesResponse, RecentChangesResult

router = APIRouter(prefix="/changes", tags=["changes"], dependencies=[CsrfDep])


@router.get("", operation_id="getRecentChanges", response_model=RecentChangesResponse)
async def get_recent_changes(change_service: ChangeServiceDep) -> RecentChangesResult:
    return await change_service.recent_changes()


@router.post("/seen", operation_id="markChangesSeen", status_code=204)
async def mark_changes_seen(change_service: ChangeServiceDep) -> None:
    await change_service.mark_changes_seen()
