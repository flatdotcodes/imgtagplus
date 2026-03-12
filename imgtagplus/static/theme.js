(() => {
    const storageKey = 'themeMode';
    const root = document.documentElement;

    function getPreferredTheme() {
        try {
            const stored = localStorage.getItem(storageKey);
            if (stored === 'dark' || stored === 'light') {
                return stored;
            }
        } catch (_) { }

        return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(mode, { persist = true } = {}) {
        const resolvedMode = mode === 'dark' ? 'dark' : 'light';
        root.classList.toggle('dark', resolvedMode === 'dark');
        root.style.colorScheme = resolvedMode;

        if (persist) {
            try {
                localStorage.setItem(storageKey, resolvedMode);
            } catch (_) { }
        }

        document.dispatchEvent(new CustomEvent('imgtagplus:theme-applied', {
            detail: { mode: resolvedMode }
        }));

        return resolvedMode;
    }

    applyTheme(getPreferredTheme(), { persist: false });

    document.addEventListener('basecoat:theme', (event) => {
        const requestedMode = event.detail?.mode;
        const fallbackMode = root.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(requestedMode || fallbackMode);
    });

    window.imgtagplusTheme = {
        applyTheme,
        getPreferredTheme,
        getCurrentTheme: () => (root.classList.contains('dark') ? 'dark' : 'light')
    };
})();
