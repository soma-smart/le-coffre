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

/**
 * Demoting this user would leave the group with no owner at all. Kept
 * distinct from GroupDomainError (rather than carrying a plain message) so
 * callers can build their own translated, name-bearing message instead of
 * showing the backend's raw id-based detail string.
 */
export class GroupLastOwnerError extends GroupDomainError {
  constructor(
    public readonly groupId: string,
    public readonly userId: string,
  ) {
    super(`User ${userId} is the last owner of group ${groupId}`)
    this.name = 'GroupLastOwnerError'
  }
}
