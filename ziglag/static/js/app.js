// ZigLag theme on top of stk's config.js. stk calls configureApp(config) at the end of config.js.
// Palette and shapes follow the explain pages: warm paper, navy ink, pastel accents, hard shadows.
function configureApp(config) {
    const vc = config.vuetifyConfig;
    vc.defaults.VChip.size = 'default';
    vc.defaults.VCard.rounded = 'xl';
    vc.defaults.VBtn.size = 'default';
    vc.defaults.VBtn.rounded = 'pill';
    vc.defaults.VDialog.rounded = 'xl';
    const ink = '#2b2e45';
    // Status and accent surfaces are pastel in both themes, so their text is always ink.
    const pastel = {
        'due-ink': ink, 'due-surface': '#f09a7c',
        'paid-ink': ink, 'paid-surface': '#a9d6c0',
        'issued-ink': ink, 'issued-surface': '#8db8e8',
        'muted-ink': ink, 'muted-surface': '#d7d9df',
        sun: '#f2cb72', 'on-sun': ink, flare: '#e8704a',
    };
    Object.assign(vc.theme.themes.light.colors, pastel, {
        primary: ink,
        'on-primary': '#f7f4ee',
        secondary: '#555a70',
        accent: '#e8704a',
        error: '#a84a28',
        info: '#2f5f9e',
        success: '#2c6e52',
        warning: '#8a5a12',
        background: '#f4f0e8',
        surface: '#f7f4ee',
        'surface-light': '#efe9de',
        'on-surface': ink,
        'on-background': ink,
        'draft-ink': ink, 'draft-surface': '#f7f4ee',
        stroke: ink, shade: ink, line: '#c9c4b8',
    });
    Object.assign(vc.theme.themes.dark.colors, pastel, {
        primary: '#f4f0e8',
        'on-primary': ink,
        secondary: '#b9bcc6',
        accent: '#e8704a',
        error: '#f09a7c',
        info: '#8db8e8',
        success: '#a9d6c0',
        warning: '#f2cb72',
        background: '#1c1e2e',
        surface: '#272a40',
        'surface-light': '#22253a',
        'on-surface': '#f4f0e8',
        'on-background': '#f4f0e8',
        'draft-ink': '#f4f0e8', 'draft-surface': '#343850',
        stroke: '#c9c4b8', shade: '#0c0d16', line: '#454a66',
    });
}
