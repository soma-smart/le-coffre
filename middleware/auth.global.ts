import { authClient } from "~/utils/auth-client";

export default defineNuxtRouteMiddleware(async (to) => {
    const publicPages = ["/login", "/register", "/setup"];
    const isPublicPage = publicPages.includes(to.path);

    // Always check session, even for public pages (for redirecting logged-in users)
    const { data: session } = await authClient.useSession(useFetch);
    const user = session.value?.user;

    if (user) {
        // If user is already logged in and tries to access login/register
        if (to.path === "/login" || to.path === "/register") {
            return navigateTo("/");
        }
    } else {
        // If not logged in and accessing a protected route
        if (!isPublicPage) {
            return navigateTo("/login");
        }
    }
});
