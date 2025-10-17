class GroupDomainException(Exception):
    pass


class GroupNameTooShortException(GroupDomainException):
    def __init__(self):
        super().__init__("Group name must be at least 10 characters long")


class GroupNameAlreadyExistsException(GroupDomainException):
    def __init__(self, name: str):
        super().__init__(f"Group with name '{name}' already exists")
