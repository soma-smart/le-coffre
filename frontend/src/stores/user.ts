import { defineStore } from 'pinia';
import { getUserMeUsersMeGet } from '@/client';
import type { GetUserMeResponse } from '@/client';

const ADMIN_ROLE = 'admin';

interface UserState {
    currentUser: GetUserMeResponse | null;
    _pending?: Promise<GetUserMeResponse | null> | null;
}

export const useUserStore = defineStore('user', {
    state: (): UserState => ({
        currentUser: null,
        _pending: null,
    }),
    
    getters: {
        /**
         * Check if the current user is an admin
         */
        isAdmin: (state): boolean => {
            if (!state.currentUser) return false;
            return state.currentUser.roles.includes(ADMIN_ROLE);
        },
        
        /**
         * Get user's display name
         */
        displayName: (state): string | null => {
            return state.currentUser?.name ?? null;
        },
        
        /**
         * Get user's email
         */
        email: (state): string | null => {
            return state.currentUser?.email ?? null;
        },
    },
    
    actions: {
        /**
         * Fetch current user information from the backend
         * Caches the result to avoid redundant API calls
         */
        async fetchCurrentUser(): Promise<GetUserMeResponse | null> {
            // Return cached value if already loaded
            if (this.currentUser !== null) {
                return this.currentUser;
            }

            // If a request is already in flight, wait for it
            if (this._pending) {
                return this._pending;
            }

            this._pending = (async () => {
                try {
                    const response = await getUserMeUsersMeGet();
                    if (response.data) {
                        this.currentUser = response.data;
                        return response.data;
                    }
                    return null;
                } catch (error) {
                    console.error('Error fetching current user:', error);
                    return null;
                } finally {
                    this._pending = null;
                }
            })();

            return this._pending;
        },
        
        /**
         * Clear user data (useful for logout)
         */
        clearUser() {
            this.currentUser = null;
            this._pending = null;
        },
    },
});
