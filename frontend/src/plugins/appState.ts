import { reactive, type App } from 'vue';

// The global reactive state for theme settings
const appState = reactive({
    theme: 'Aura',
    darkTheme: false
});

export default {
    install: (app: App) => {
        // Make the state available in all components as this.$appState
        app.config.globalProperties.$appState = appState;
    }
};
