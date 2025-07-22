from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide

from src.application.usecase.setup_master_password import SetupMasterPasswordUseCase
from src.domain.setup_info import SetupInfo

router = APIRouter()


@router.post("/setup")
@inject
def setup_master_password(
    nb_shared: int,
    threshold: int,
    usecase: SetupMasterPasswordUseCase = Depends(
        Provide["setup_master_password_usecase"]
    ),
):
    try:
        setup_info: SetupInfo = usecase.execute(nb_shared, threshold)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return "yolo"
