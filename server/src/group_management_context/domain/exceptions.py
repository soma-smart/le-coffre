class GroupDomainException(Exception):
    pass


class GroupNameTooShortException(GroupDomainException):
    def __init__(self, min_len: int):
        super().__init__(f"Group name must be at least {min_len} characters long")


class GroupNameAlreadyExistsException(GroupDomainException):
    def __init__(self, name: str):
        super().__init__(f"Group with name '{name}' already exists")
