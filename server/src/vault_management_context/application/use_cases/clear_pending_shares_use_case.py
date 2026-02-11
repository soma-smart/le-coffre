from vault_management_context.application.commands import ClearPendingSharesCommand
from vault_management_context.application.gateways import ShareRepository


class ClearPendingSharesUseCase:
    """Use case to clear all pending shares without unlocking"""

    def __init__(self, share_repository: ShareRepository) -> None:
        self.share_repository = share_repository

    def execute(self, command: ClearPendingSharesCommand) -> None:
        """Clear all pending shares from the repository"""
        self.share_repository.clear()
