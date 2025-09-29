from fastapi import Depends
from starlette.requests import Request

from user_management_context.application.use_cases import (
    GetUserUseCase,
    DeleteUserUseCase,
    UpdateUserUseCase,
    CreateUserUseCase,
    ListUserUseCase,
)
from user_management_context.application.interfaces import UserRepository


def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository


def get_get_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return GetUserUseCase(user_repository)


def get_delete_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return DeleteUserUseCase(user_repository)


def get_update_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return UpdateUserUseCase(user_repository)


def get_create_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return CreateUserUseCase(user_repository)


def get_list_user_usecase(
    user_repository: UserRepository = Depends(get_user_repository),
):
    return ListUserUseCase(user_repository)
