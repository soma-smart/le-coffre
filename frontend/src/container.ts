import type { CsrfGateway } from '@/application/ports/CsrfGateway'
import type { GroupRepository } from '@/application/ports/GroupRepository'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import type { UserRepository } from '@/application/ports/UserRepository'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import { FetchCsrfTokenUseCase } from '@/application/csrf/FetchCsrfToken'
import { AddMemberToGroupUseCase } from '@/application/group/AddMemberToGroup'
import { CreateGroupUseCase } from '@/application/group/CreateGroup'
import { DeleteGroupUseCase } from '@/application/group/DeleteGroup'
import { GetGroupUseCase } from '@/application/group/GetGroup'
import { ListGroupsUseCase } from '@/application/group/ListGroups'
import { PromoteMemberToOwnerUseCase } from '@/application/group/PromoteMemberToOwner'
import { RemoveMemberFromGroupUseCase } from '@/application/group/RemoveMemberFromGroup'
import { UpdateGroupUseCase } from '@/application/group/UpdateGroup'
import { CreatePasswordUseCase } from '@/application/password/CreatePassword'
import { DeletePasswordUseCase } from '@/application/password/DeletePassword'
import { GetPasswordUseCase } from '@/application/password/GetPassword'
import { ListPasswordAccessUseCase } from '@/application/password/ListPasswordAccess'
import { ListPasswordEventsUseCase } from '@/application/password/ListPasswordEvents'
import { ListPasswordsUseCase } from '@/application/password/ListPasswords'
import { SharePasswordUseCase, UnsharePasswordUseCase } from '@/application/password/SharePassword'
import { UpdatePasswordUseCase } from '@/application/password/UpdatePassword'
import { ClearPendingSharesUseCase } from '@/application/vault/ClearPendingShares'
import { CreateVaultUseCase } from '@/application/vault/CreateVault'
import { GetVaultStatusUseCase } from '@/application/vault/GetVaultStatus'
import { LockVaultUseCase } from '@/application/vault/LockVault'
import { UnlockVaultUseCase } from '@/application/vault/UnlockVault'
import { ValidateVaultSetupUseCase } from '@/application/vault/ValidateVaultSetup'
import { CreateUserUseCase } from '@/application/user/CreateUser'
import { DeleteUserUseCase } from '@/application/user/DeleteUser'
import { GetCurrentUserUseCase } from '@/application/user/GetCurrentUser'
import { GetUserUseCase } from '@/application/user/GetUser'
import { ListUsersUseCase } from '@/application/user/ListUsers'
import { PromoteUserToAdminUseCase } from '@/application/user/PromoteUserToAdmin'
import { UpdateUserUseCase } from '@/application/user/UpdateUser'
import { UpdateUserPasswordUseCase } from '@/application/user/UpdateUserPassword'

/**
 * Framework-free container — holds every use case the presentation
 * layer needs. Vue imports nothing from this file; `plugins/container.ts`
 * is the only Vue-aware bridge. Tests build their own container with
 * in-memory fakes; production wires backend adapters via
 * `composition_root.ts`.
 *
 * Features are added one bounded context at a time, each extending
 * `Ports` and `Container`.
 */

export interface Ports {
  passwordRepository: PasswordRepository
  csrfGateway: CsrfGateway
  userRepository: UserRepository
  groupRepository: GroupRepository
  vaultRepository: VaultRepository
}

export interface Container {
  passwords: {
    list: ListPasswordsUseCase
    get: GetPasswordUseCase
    create: CreatePasswordUseCase
    update: UpdatePasswordUseCase
    delete: DeletePasswordUseCase
    share: SharePasswordUseCase
    unshare: UnsharePasswordUseCase
    listAccess: ListPasswordAccessUseCase
    listEvents: ListPasswordEventsUseCase
  }
  csrf: {
    fetchToken: FetchCsrfTokenUseCase
  }
  users: {
    getCurrent: GetCurrentUserUseCase
    get: GetUserUseCase
    list: ListUsersUseCase
    create: CreateUserUseCase
    update: UpdateUserUseCase
    updatePassword: UpdateUserPasswordUseCase
    delete: DeleteUserUseCase
    promoteToAdmin: PromoteUserToAdminUseCase
  }
  groups: {
    list: ListGroupsUseCase
    get: GetGroupUseCase
    create: CreateGroupUseCase
    update: UpdateGroupUseCase
    delete: DeleteGroupUseCase
    addMember: AddMemberToGroupUseCase
    removeMember: RemoveMemberFromGroupUseCase
    promoteToOwner: PromoteMemberToOwnerUseCase
  }
  vault: {
    getStatus: GetVaultStatusUseCase
    create: CreateVaultUseCase
    validateSetup: ValidateVaultSetupUseCase
    unlock: UnlockVaultUseCase
    lock: LockVaultUseCase
    clearPendingShares: ClearPendingSharesUseCase
  }
}

export function buildContainer(ports: Ports): Container {
  return {
    passwords: {
      list: new ListPasswordsUseCase(ports.passwordRepository),
      get: new GetPasswordUseCase(ports.passwordRepository),
      create: new CreatePasswordUseCase(ports.passwordRepository),
      update: new UpdatePasswordUseCase(ports.passwordRepository),
      delete: new DeletePasswordUseCase(ports.passwordRepository),
      share: new SharePasswordUseCase(ports.passwordRepository),
      unshare: new UnsharePasswordUseCase(ports.passwordRepository),
      listAccess: new ListPasswordAccessUseCase(ports.passwordRepository),
      listEvents: new ListPasswordEventsUseCase(ports.passwordRepository),
    },
    csrf: {
      fetchToken: new FetchCsrfTokenUseCase(ports.csrfGateway),
    },
    users: {
      getCurrent: new GetCurrentUserUseCase(ports.userRepository),
      get: new GetUserUseCase(ports.userRepository),
      list: new ListUsersUseCase(ports.userRepository),
      create: new CreateUserUseCase(ports.userRepository),
      update: new UpdateUserUseCase(ports.userRepository),
      updatePassword: new UpdateUserPasswordUseCase(ports.userRepository),
      delete: new DeleteUserUseCase(ports.userRepository),
      promoteToAdmin: new PromoteUserToAdminUseCase(ports.userRepository),
    },
    groups: {
      list: new ListGroupsUseCase(ports.groupRepository),
      get: new GetGroupUseCase(ports.groupRepository),
      create: new CreateGroupUseCase(ports.groupRepository),
      update: new UpdateGroupUseCase(ports.groupRepository),
      delete: new DeleteGroupUseCase(ports.groupRepository),
      addMember: new AddMemberToGroupUseCase(ports.groupRepository),
      removeMember: new RemoveMemberFromGroupUseCase(ports.groupRepository),
      promoteToOwner: new PromoteMemberToOwnerUseCase(ports.groupRepository),
    },
    vault: {
      getStatus: new GetVaultStatusUseCase(ports.vaultRepository),
      create: new CreateVaultUseCase(ports.vaultRepository),
      validateSetup: new ValidateVaultSetupUseCase(ports.vaultRepository),
      unlock: new UnlockVaultUseCase(ports.vaultRepository),
      lock: new LockVaultUseCase(ports.vaultRepository),
      clearPendingShares: new ClearPendingSharesUseCase(ports.vaultRepository),
    },
  }
}
