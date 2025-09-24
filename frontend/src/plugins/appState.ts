import { reactive, type App } from 'vue';

export default {
    install: (app: App) => {
        const _appState = reactive({ theme: 'Aura', darkTheme: false });

        app.config.globalProperties.$appState = _appState;
    }
};
