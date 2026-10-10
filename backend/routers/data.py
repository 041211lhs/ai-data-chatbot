"""데이터 API. 라우터는 주소·입출력 형식만 정하고 실제 일은 services에 맡긴다."""
from fastapi import APIRouter, HTTPException, status

from schemas import DataCreate, DataItem, DataUpdate
from services import data_service
from services.summary_service import build_statistics, build_summary

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/summary", summary="데이터 요약 (프롬프트 주입용)")
def get_summary():
    return build_summary(data_service.list_data())


@router.get("/statistics", summary="그래프용 통계 (12개월 이동평균, 전년 동월 대비)")
def get_statistics():
    return build_statistics(data_service.list_data())


@router.get("", response_model=list[DataItem], summary="데이터 목록 (날짜순)")
def list_data():
    return data_service.list_data()


@router.post("", response_model=DataItem, status_code=status.HTTP_201_CREATED, summary="데이터 추가")
def create_data(body: DataCreate):
    return data_service.create_data(body.date, body.value, body.memo)


@router.put("/{item_id}", response_model=DataItem, summary="데이터 수정 (바꿀 필드만)")
def update_data(item_id: str, body: DataUpdate):
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="수정할 필드가 없다")
    return data_service.update_data(item_id, changes)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="데이터 삭제")
def delete_data(item_id: str):
    data_service.delete_data(item_id)
