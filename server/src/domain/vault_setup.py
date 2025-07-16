from src.domain.setup_info import SetupInfo
from .crypto.shamir_service import ShamirSecretService


def setup_master_password(
    setup_info: SetupInfo | None, nb_shared: int, threshold: int
) -> SetupInfo:
    if setup_info is not None:
        raise Exception("Already setup")
    if nb_shared < 2:
        raise Exception("Number of shares must be at least 2")
    if threshold < 2:
        raise Exception("Threshold must be at least 2")
    if threshold > nb_shared:
        raise Exception("Threshold cannot be greater than number of shares")

    shares = ShamirSecretService().split_secret(threshold, nb_shared)
    return SetupInfo(shares=shares)
