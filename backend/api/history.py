from typing import Literal

from fastapi import APIRouter, Query, Request

from backend.models import HistoryPage

router=APIRouter(prefix="/api/history", tags=["history"])
@router.get("",response_model=HistoryPage)
def history(request: Request,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),ticker:str|None=None,status:Literal["queued","running","completed","failed"]|None=None,signal:Literal["BUY","OVERWEIGHT","HOLD","UNDERWEIGHT","SELL","REVIEW"]|None=None,sort_by:Literal["created_at","ticker","analysis_date","status","signal"]="created_at",sort_order:Literal["asc","desc"]="desc") -> HistoryPage:
    return request.app.state.store.list_runs(page=page,page_size=page_size,ticker=ticker,status=status,signal=signal,sort_by=sort_by,sort_order=sort_order)
