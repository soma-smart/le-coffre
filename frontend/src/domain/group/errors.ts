export class GroupDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'GroupDomainError'
  }
}

export class GroupNotFoundError extends GroupDomainError {
  constructor(public readonly groupId: string) {
    super(`Group ${groupId} not found`)
    this.name = 'GroupNotFoundError'
  }
}

export class GroupAccessDeniedError extends GroupDomainError {
  constructor(public readonly groupId: string) {
    super(`Access to group ${groupId} was denied`)
    this.name = 'GroupAccessDeniedError'
  }
}

export class GroupNameRequiredError extends GroupDomainError {
  constructor() {
    super('Group name is required')
    this.name = 'GroupNameRequiredError'
  }
}

export class GroupUserRequiredError extends GroupDomainError {
  constructor() {
    super('A user id is required for this operation')
    this.name = 'GroupUserRequiredError'
  }
}
