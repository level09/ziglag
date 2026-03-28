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
                size: 'small',
                rounded: 'sm'
            },
            VCard: {
                elevation: 0,
                rounded: 0
            },
            VMenu: {
                offset: 10
            },
            VBtn: {
                variant: 'elevated',
                size: 'small',
                rounded: 0
            },
            VDialog: {
                rounded: 0
            },
            VToolbar: {
                elevation: 0
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
                },
                dark: {
                    dark: true,
                    colors: {
                        primary: '#bfc2ff',
                        'primary-container': '#353aaf',
                        secondary: '#bfc1ff',
                        'secondary-container': '#363a9c',
                        tertiary: '#dbc0c6',
                        'tertiary-container': '#554247',
                        error: '#ffb4ab',
                        'error-container': '#93000a',
                        background: '#131314',
                        surface: '#131314',
                        'surface-bright': '#3a3a3c',
                        'surface-dim': '#131314',
                        'surface-container-lowest': '#0e0e0f',
                        'surface-container-low': '#1b1c1c',
                        'surface-container': '#1f2020',
                        'surface-container-high': '#2a2a2b',
                        'surface-container-highest': '#353536',
                        'surface-variant': '#464653',
                        'on-surface': '#e5e2e1',
                        'on-surface-variant': '#c6c5d5',
                        'on-primary': '#1b1f90',
                        'on-primary-container': '#dbdbff',
                        'on-secondary': '#1c2090',
                        'on-tertiary': '#3e2b30',
                        'on-error': '#690005',
                        'on-background': '#e5e2e1',
                        'outline': '#908f9f',
                        'outline-variant': '#464653',
                        'inverse-surface': '#e5e2e1',
                        'inverse-on-surface': '#303030',
                        'inverse-primary': '#4a50c4',
                        info: '#bfc2ff',
                        success: '#4ade80',
                        warning: '#fde047',
                    }
                }
            }
        }
    }
};
