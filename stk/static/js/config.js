/**
 * ZigLag - Central Configuration
 * Neo-brutalist editorial design system
 */

const config = {
    // Common Vue settings
    delimiters: ['${', '}'],

    // Vuetify configuration
    vuetifyConfig: {
        defaults: {
            VTextField: {
                variant: 'outlined'
            },
            VSelect: {
                variant: 'outlined'
            },
            VTextarea: {
                variant: 'outlined'
            },
            VCombobox: {
                variant: 'outlined'
            },
            VAutocomplete: {
                variant: 'outlined'
            },
            VChip: {
                size: 'small'
            },
            VCard: {
                elevation: 0,
                rounded: 'xl'
            },
            VMenu: {
                offset: 10
            },
            VBtn: {
                variant: 'elevated',
                size: 'small'
            },
            VDataTableServer: {
                itemsPerPage: 25,
                itemsPerPageOptions: [25, 50, 100]
            }
        },
        theme: {
            defaultTheme: 'light',
            themes: {
                light: {
                    dark: false,
                    colors: {
                        primary: '#353aaf',
                        'primary-container': '#4e54c8',
                        secondary: '#4f53b6',
                        'secondary-container': '#9297fe',
                        tertiary: '#59454a',
                        'tertiary-container': '#725c62',
                        error: '#ba1a1a',
                        'error-container': '#ffdad6',
                        background: '#fbf9f8',
                        surface: '#fbf9f8',
                        'surface-bright': '#fbf9f8',
                        'surface-dim': '#dcd9d9',
                        'surface-container-lowest': '#ffffff',
                        'surface-container-low': '#f6f3f2',
                        'surface-container': '#f0eded',
                        'surface-container-high': '#eae8e7',
                        'surface-container-highest': '#e4e2e1',
                        'surface-variant': '#e4e2e1',
                        'on-surface': '#1b1c1c',
                        'on-surface-variant': '#464653',
                        'on-primary': '#ffffff',
                        'on-primary-container': '#dbdbff',
                        'on-secondary': '#ffffff',
                        'on-tertiary': '#ffffff',
                        'on-error': '#ffffff',
                        'on-background': '#1b1c1c',
                        'outline': '#767685',
                        'outline-variant': '#c6c5d5',
                        'inverse-surface': '#303030',
                        'inverse-on-surface': '#f3f0f0',
                        'inverse-primary': '#bfc2ff',
                        info: '#353aaf',
                        success: '#16A34A',
                        warning: '#EAB308',
                    }
                }
            }
        }
    }
};
