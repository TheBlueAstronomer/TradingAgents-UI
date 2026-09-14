from fastapi import APIRouter

from backend.models import AnalystOption, ModelOption, ProviderOption

router=APIRouter(prefix="/api/config", tags=["config"])
@router.get("/providers", response_model=list[ProviderOption])
def providers() -> list[ProviderOption]:
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
    result=[]
    for key, modes in MODEL_OPTIONS.items():
        quick=[ModelOption(label=a,value=b) for a,b in modes["quick"]]; deep=[ModelOption(label=a,value=b) for a,b in modes["deep"]]
        result.append(ProviderOption(id=key,label=key.replace("_"," ").title(),quick_models=quick,deep_models=deep,allows_custom_model=any(x.value=="custom" for x in quick+deep),requires_backend_url=key=="openai_compatible",default_quick_model=quick[0].value,default_deep_model=deep[0].value))
    return result
@router.get("/analysts", response_model=list[AnalystOption])
def analysts() -> list[AnalystOption]:
    return [AnalystOption(id="market",label="Market Analyst",description="Market data and technical evidence",selected_by_default=True),AnalystOption(id="social",label="Sentiment Analyst",description="Public sentiment evidence",selected_by_default=True),AnalystOption(id="news",label="News Analyst",description="News and macro evidence",selected_by_default=True),AnalystOption(id="fundamentals",label="Fundamentals Analyst",description="Company fundamentals",selected_by_default=True)]
