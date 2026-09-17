<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import type { AccessRole, Password, ShareStatus } from '@/domain/password/Password'
import { severityForShareStatus, shareStatusOf } from '@/domain/password/Password'
import { PasswordDomainError } from '@/domain/password/errors'
import { useContainer } from '@/plugins/container'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordAccessStore } from '@/stores/passwordAccess'
import { sortGroupsByName } from '@/utils/groupSort'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  password?: Password | null
}>()

const emit = defineEmits<{
  (e: 'shared'): void
  (e: 'unshared'): void
}>()

interface AccessLinkView {
  groupId: string
  groupName: string
  roleInGroup: AccessRole
  groupRole: AccessRole
  expiresAt: string | null
}

interface UserAccessView {
  userId: string
  displayName?: string
  loadingName: boolean
  links: AccessLinkView[]
}

interface GroupAccessView {
  groupId: string
  groupName: string
  role: AccessRole
  expiresAt: string | null
}

const toast = useToast()
const { t } = useI18n()
const groupsStore = useGroupsStore()
const passwordAccessStore = usePasswordAccessStore()
const { groups: allGroups } = storeToRefs(groupsStore)

// Resolve use cases at setup time — inject() has no active instance
// inside async handlers after an await.
const { passwords: passwordUseCases, users: userUseCases } = useContainer()

const selectedGroupId = ref<string>('')
const shareExpiresAt = ref<string | null>(null)
// The group whose deadline is currently being edited, or null when nobody is.
const retimingGroupId = ref<string | null>(null)
const retimeExpiresAt = ref<string | null>(null)
const loading = ref(false)
const loadingAccess = ref(false)
const userAccessList = ref<UserAccessView[]>([])
const groupAccessList = ref<GroupAccessView[]>([])
const canManageSharing = computed(() => !!props.password?.canWrite)

// Get groups that can be shared with (excluding groups that already have access), sorted by name
const availableGroupsForSharing = computed(() => {
  const groupsWithAccessIds = new Set(groupAccessList.value.map((g) => g.groupId))
  const filtered = allGroups.value.filter((g) => !groupsWithAccessIds.has(g.id))
  return sortGroupsByName(filtered)
})

// An owning group never expires, so it carries no badge; a shared group shows
// either its countdown or the fact that it already lapsed.
const shareStatus = (expiresAt: string | null): ShareStatus => shareStatusOf(expiresAt)

const shareLabel = (expiresAt: string | null): string =>
  shareStatus(expiresAt) === 'expired'
    ? t('components.sharePasswordModal.expiredLabel')
    : t('components.sharePasswordModal.expiresLabel', {
        relative: formatRelativeTime(expiresAt ?? ''),
      })

// A user is a password "owner" when they own a group that owns the password.
const userIsOwner = (user: UserAccessView): boolean =>
  user.links.some((link) => link.roleInGroup === 'owner' && link.groupRole === 'owner')

// Fetch user display name by user ID
const fetchUserDisplayName = async (userId: string): Promise<string> => {
  try {
    const user = await userUseCases.get.execute({ userId })
    return user.name || userId
  } catch (error) {
    console.log(error)
    return userId
  }
}

// Resolve a group name from the already-loaded group list, falling back to the id.
const groupName = (groupId: string): string => {
  const group = allGroups.value.find((g) => g.id === groupId)
  return group?.name ?? groupId
}

// Load the access links and fold the per-(user, group) rows into one card per user.
const loadAccessList = async () => {
  if (!props.password) return

  loadingAccess.value = true
  try {
    const access = await passwordUseCases.listAccess.execute({
      passwordId: props.password.id,
    })

    const byUser = new Map<string, UserAccessView>()
    for (const link of access.users) {
      const view = byUser.get(link.userId) ?? { userId: link.userId, loadingName: true, links: [] }
      view.links.push({
        groupId: link.groupId,
        groupName: groupName(link.groupId),
        roleInGroup: link.roleInGroup,
        groupRole: link.groupRole,
        expiresAt: link.expiresAt,
      })
      byUser.set(link.userId, view)
    }
    userAccessList.value = Array.from(byUser.values())

    groupAccessList.value = access.groups.map((group) => ({
      groupId: group.groupId,
      groupName: groupName(group.groupId),
      role: group.role,
      expiresAt: group.expiresAt,
    }))

    for (const user of userAccessList.value) {
      user.displayName = await fetchUserDisplayName(user.userId)
      user.loadingName = false
    }
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('components.sharePasswordModal.loadAccessFailed'),
      life: 5000,
    })
  } finally {
    loadingAccess.value = false
  }
}

// Watch for password changes
watch(
  () => props.password,
  async (newPassword) => {
    if (newPassword && visible.value) {
      await loadAccessList()
    }
  },
  { immediate: true },
)

// Watch for modal visibility
watch(visible, async (isVisible) => {
  if (isVisible && props.password) {
    await groupsStore.fetchAllGroups()
    await loadAccessList()
    selectedGroupId.value = ''
    shareExpiresAt.value = null
    retimingGroupId.value = null
  }
})

// Share password with group
const sharePassword = async () => {
  if (!props.password || !selectedGroupId.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.sharePasswordModal.groupRequired'),
      life: 5000,
    })
    return
  }

  if (!canManageSharing.value) {
    toast.add({
      severity: 'error',
      summary: t('components.sharePasswordModal.permissionDeniedSummary'),
      detail: t('components.sharePasswordModal.shareForbidden'),
      life: 5000,
    })
    return
  }

  loading.value = true
  try {
    await passwordUseCases.share.execute({
      passwordId: props.password.id,
      groupId: selectedGroupId.value,
      expiresAt: shareExpiresAt.value,
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: shareExpiresAt.value
        ? t('components.sharePasswordModal.sharedUntil', {
            date: formatAbsoluteTime(shareExpiresAt.value),
          })
        : t('components.sharePasswordModal.sharedSuccessfully'),
      life: 5000,
    })

    selectedGroupId.value = ''
    shareExpiresAt.value = null
    passwordAccessStore.invalidatePasswordAccess()
    await loadAccessList()
    emit('shared')
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail:
        error instanceof PasswordDomainError
          ? error.message
          : t('components.sharePasswordModal.shareFailedFallback'),
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

// Unshare password from group
const unshareFromGroup = async (groupId: string) => {
  if (!props.password) return

  if (!canManageSharing.value) {
    toast.add({
      severity: 'error',
      summary: t('components.sharePasswordModal.permissionDeniedSummary'),
      detail: t('components.sharePasswordModal.unshareForbidden'),
      life: 5000,
    })
    return
  }

  loading.value = true
  try {
    await passwordUseCases.unshare.execute({
      passwordId: props.password.id,
      groupId,
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.sharePasswordModal.unshareSuccessfully'),
      life: 5000,
    })

    await groupsStore.fetchAllGroups(true)
    passwordAccessStore.invalidatePasswordAccess()
    await loadAccessList()

    emit('unshared')
  } catch (error) {
    const detail =
      error instanceof PasswordDomainError
        ? error.message
        : t('components.sharePasswordModal.unshareFailedFallback')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const startRetiming = (group: GroupAccessView) => {
  retimingGroupId.value = group.groupId
  retimeExpiresAt.value = group.expiresAt
}

const cancelRetiming = () => {
  retimingGroupId.value = null
  retimeExpiresAt.value = null
}

const saveRetiming = async (groupId: string) => {
  if (!props.password) return

  loading.value = true
  try {
    await passwordUseCases.updateShareExpiration.execute({
      passwordId: props.password.id,
      groupId,
      expiresAt: retimeExpiresAt.value,
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: retimeExpiresAt.value
        ? t('components.sharePasswordModal.accessUntil', {
            date: formatAbsoluteTime(retimeExpiresAt.value),
          })
        : t('components.sharePasswordModal.accessNowPermanent'),
      life: 5000,
    })

    cancelRetiming()
    passwordAccessStore.invalidatePasswordAccess()
    await loadAccessList()
    emit('shared')
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail:
        error instanceof PasswordDomainError
          ? error.message
          : t('components.sharePasswordModal.retimeFailedFallback'),
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await groupsStore.fetchAllGroups()
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.sharePasswordModal.title')"
    :style="{ width: '36rem' }"
  >
    <div v-if="loadingAccess" class="flex justify-center py-4">
      <ProgressSpinner />
    </div>

    <div
      v-else
      class="flex flex-col gap-4"
      @keydown.enter.prevent="canManageSharing && !!selectedGroupId && !loading && sharePassword()"
    >
      <!-- Share with new group (only for users with write access) -->
      <div v-if="canManageSharing" class="flex flex-col gap-4 pb-4 border-b">
        <h3 class="font-semibold text-lg">
          {{ t('components.sharePasswordModal.shareWithGroupTitle') }}
        </h3>
        <div class="flex gap-2">
          <Select
            id="group-select"
            v-model="selectedGroupId"
            :options="availableGroupsForSharing"
            :optionLabel="(group) => group.name"
            optionValue="id"
            :placeholder="t('components.sharePasswordModal.selectGroupPlaceholder')"
            :disabled="loading"
            filter
            :filterPlaceholder="t('components.sharePasswordModal.searchGroupsPlaceholder')"
            class="flex-1"
          >
            <template #option="slotProps">
              <div class="flex items-center gap-2">
                <i class="pi pi-users text-sm"></i>
                <span>{{ slotProps.option.name }}</span>
              </div>
            </template>
          </Select>
          <Button
            :label="t('components.sharePasswordModal.shareButton')"
            icon="pi pi-share-alt"
            @click="sharePassword"
            :loading="loading"
            :disabled="!selectedGroupId || loading"
          />
        </div>
        <ShareDurationPicker v-model="shareExpiresAt" :disabled="loading" />
      </div>

      <Tabs value="users">
        <TabList>
          <Tab value="users">{{ t('components.sharePasswordModal.usersTab') }}</Tab>
          <Tab value="groups">{{ t('components.sharePasswordModal.groupsTab') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="users">
            <div class="flex flex-col gap-3 pt-4">
              <div v-if="userAccessList.length === 0" class="text-center py-4 text-muted-color">
                <p>{{ t('components.sharePasswordModal.noUsersYet') }}</p>
              </div>

              <div v-else class="space-y-2">
                <Card
                  v-for="user in userAccessList"
                  :key="user.userId"
                  class="hover:bg-surface-50 transition-colors"
                >
                  <template #content>
                    <div class="flex items-center gap-3">
                      <i class="pi pi-user text-xl text-primary"></i>
                      <div>
                        <p class="font-semibold">
                          <Skeleton v-if="user.loadingName" width="10rem" height="1rem" />
                          <span v-else>{{ user.displayName }}</span>
                        </p>
                        <div class="flex gap-2 items-center text-sm text-muted-color">
                          <span v-if="userIsOwner(user)" class="flex items-center gap-1">
                            <i class="pi pi-crown text-yellow-500"></i>
                            {{ t('components.sharePasswordModal.ownerLabel') }}
                          </span>
                          <span v-else class="flex items-center gap-1">
                            <i class="pi pi-eye"></i>
                            {{ t('components.sharePasswordModal.canReadLabel') }}
                          </span>
                        </div>
                        <div
                          class="flex flex-wrap gap-2 items-center text-sm text-muted-color mt-1"
                        >
                          <span class="flex items-center gap-1">
                            <i class="pi pi-users"></i>
                            {{ t('components.sharePasswordModal.viaLabel') }}
                          </span>
                          <span
                            v-for="link in user.links"
                            :key="link.groupId"
                            class="surface-100 px-2 py-1 rounded flex items-center gap-1"
                            v-tooltip="
                              (link.roleInGroup === 'owner'
                                ? t('components.sharePasswordModal.ownerOfGroupRole')
                                : t('components.sharePasswordModal.memberOfGroupRole')) +
                              ' ' +
                              t('components.sharePasswordModal.ofThisGroup') +
                              ' · ' +
                              (link.groupRole === 'owner'
                                ? t('components.sharePasswordModal.ownsScope')
                                : t('components.sharePasswordModal.sharedScope'))
                            "
                          >
                            <i
                              :class="
                                link.roleInGroup === 'owner'
                                  ? 'pi pi-crown text-yellow-500'
                                  : 'pi pi-user'
                              "
                            ></i>
                            {{ link.groupName }}
                            <Tag
                              :value="
                                link.groupRole === 'owner'
                                  ? t('components.sharePasswordModal.ownsTag')
                                  : t('components.sharePasswordModal.sharedTag')
                              "
                              :severity="link.groupRole === 'owner' ? 'success' : 'info'"
                            />
                            <Tag
                              v-if="link.expiresAt"
                              :value="shareLabel(link.expiresAt)"
                              :severity="severityForShareStatus(shareStatus(link.expiresAt))"
                              :title="formatAbsoluteTime(link.expiresAt)"
                              data-testid="user-share-expiry"
                            />
                          </span>
                        </div>
                      </div>
                    </div>
                  </template>
                </Card>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="groups">
            <div class="flex flex-col gap-3 pt-4">
              <div v-if="groupAccessList.length === 0" class="text-center py-4 text-muted-color">
                <p>{{ t('components.sharePasswordModal.noGroupsYet') }}</p>
              </div>

              <div v-else class="space-y-2">
                <Card
                  v-for="group in groupAccessList"
                  :key="group.groupId"
                  class="hover:bg-surface-50 transition-colors"
                >
                  <template #content>
                    <div class="flex justify-between items-center">
                      <div class="flex items-center gap-3">
                        <i class="pi pi-users text-xl text-primary"></i>
                        <div>
                          <p class="font-semibold">{{ group.groupName }}</p>
                          <div class="flex gap-2 items-center text-sm text-muted-color">
                            <span v-if="group.role === 'owner'" class="flex items-center gap-1">
                              <i class="pi pi-crown text-yellow-500"></i>
                              {{ t('components.sharePasswordModal.ownerGroupLabel') }}
                            </span>
                            <span v-else class="flex items-center gap-1">
                              <i class="pi pi-share-alt"></i>
                              {{ t('components.sharePasswordModal.sharedLabel') }}
                            </span>
                            <Tag
                              v-if="group.expiresAt"
                              :value="shareLabel(group.expiresAt)"
                              :severity="severityForShareStatus(shareStatus(group.expiresAt))"
                              :title="formatAbsoluteTime(group.expiresAt)"
                              data-testid="group-share-expiry"
                            />
                          </div>
                        </div>
                      </div>

                      <div
                        v-if="canManageSharing && group.role !== 'owner'"
                        class="flex items-center gap-1"
                      >
                        <Button
                          icon="pi pi-clock"
                          text
                          rounded
                          size="small"
                          :aria-label="t('components.sharePasswordModal.changeDurationAria')"
                          :disabled="loading"
                          @click="startRetiming(group)"
                          v-tooltip="t('components.sharePasswordModal.changeDurationTooltip')"
                          data-testid="change-duration"
                        />
                        <Button
                          icon="pi pi-times"
                          text
                          rounded
                          severity="danger"
                          size="small"
                          :aria-label="t('components.sharePasswordModal.revokeAccessAria')"
                          :loading="loading"
                          @click="unshareFromGroup(group.groupId)"
                          v-tooltip="t('components.sharePasswordModal.revokeAccessTooltip')"
                        />
                      </div>
                    </div>

                    <div
                      v-if="retimingGroupId === group.groupId"
                      class="mt-3 pt-3 border-t flex flex-col gap-2"
                      data-testid="retime-form"
                    >
                      <ShareDurationPicker v-model="retimeExpiresAt" :disabled="loading" />
                      <div class="flex justify-end gap-2">
                        <Button
                          :label="t('components.sharePasswordModal.cancelButton')"
                          severity="secondary"
                          size="small"
                          text
                          :disabled="loading"
                          @click="cancelRetiming"
                        />
                        <Button
                          :label="t('components.sharePasswordModal.saveButton')"
                          size="small"
                          :loading="loading"
                          @click="saveRetiming(group.groupId)"
                        />
                      </div>
                    </div>
                  </template>
                </Card>
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <template #footer>
      <Button
        :label="t('components.sharePasswordModal.closeButton')"
        severity="secondary"
        @click="visible = false"
        :disabled="loading"
      />
    </template>
  </Dialog>
</template>
