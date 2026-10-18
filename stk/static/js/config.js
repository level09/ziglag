/**
 * stk Framework - Central Configuration
 * Shared workspace theme
 */

const config = {
    // Common Vue settings
    delimiters: ['${', '}'],

    // Vuetify configuration
    vuetifyConfig: {
        // Tabler icon set for Vuetify's internal component icons (data-table
        // sort/pagination, select dropdown, checkboxes, alerts). Without this
        // Vuetify defaults to mdi aliases, which render blank since we ship no
        // MDI font. Pass-through any explicit "ti ti-*" string; prefix bare names.
        icons: {
            defaultSet: 'tabler',
            sets: {
                tabler: {
                    component: (props) => {
                        const icon = props.icon || '';
                        const cls = (icon.startsWith('ti ') || icon.startsWith('ti-'))
                            ? icon
                            : `ti ti-${icon}`;
                        return Vue.h(props.tag, { class: cls });
                    }
                }
            },
            aliases: {
                complete: 'check',
                cancel: 'circle-x',
                close: 'x',
                delete: 'x',
                clear: 'circle-x',
                success: 'circle-check',
                info: 'info-circle',
                warning: 'alert-triangle',
                error: 'alert-circle',
                prev: 'chevron-left',
                next: 'chevron-right',
                checkboxOn: 'square-check',
                checkboxOff: 'square',
                checkboxIndeterminate: 'square-minus',
                delimiter: 'circle',
                sortAsc: 'arrow-up',
                sortDesc: 'arrow-down',
                expand: 'chevron-down',
                menu: 'menu-2',
                subgroup: 'chevron-down',
                dropdown: 'chevron-down',
                radioOn: 'circle-check',
                radioOff: 'circle',
                edit: 'pencil',
                ratingEmpty: 'star',
                ratingFull: 'star-filled',
                ratingHalf: 'star-half-filled',
                loading: 'loader-2',
                first: 'chevrons-left',
                last: 'chevrons-right',
                unfold: 'arrows-sort',
                file: 'paperclip',
                plus: 'plus',
                minus: 'minus',
                calendar: 'calendar',
                treeviewCollapse: 'chevron-down',
                treeviewExpand: 'chevron-right',
                eyeDropper: 'color-picker',
                upload: 'upload',
                color: 'palette'
            }
        },
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
            VChip: {
                size: 'default',
                rounded: 'sm'
            },
            VCard: {
                elevation: 0,
                rounded: 'lg'
            },
            VMenu: {
                offset: 10
            },
            VBtn: {
                variant: 'elevated',
                size: 'default',
                rounded: 'lg'
            },
            VDialog: {
                rounded: 'lg'
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
            defaultTheme: window.__settings__?.dark ? 'dark' : 'light',
            themes: {
                light: {
                    dark: false,
                    colors: {
                        primary: '#116b59',
                        'on-primary': '#ffffff',
                        secondary: '#64756f',
                        accent: '#116b59',
                        error: '#b33545',
                        info: '#255da8',
                        success: '#18734f',
                        warning: '#8c5314',
                        background: '#f4f6f5',
                        surface: '#ffffff',
                        'surface-light': '#f0f3f2',
                        'on-surface': '#263b35',
                        'on-background': '#263b35',
                        'draft-ink': '#53675f', 'draft-surface': '#f0f3f2',
                        'due-ink': '#915216', 'due-surface': '#fff2dc',
                        'paid-ink': '#1b704d', 'paid-surface': '#e4f4ec',
                        'issued-ink': '#285e4e', 'issued-surface': '#eaf2ef',
                        'muted-ink': '#64756f', 'muted-surface': '#f0f3f2',
                    }
                },
                dark: {
                    dark: true,
                    colors: {
                        primary: '#77e2c4',
                        'on-primary': '#10362e',
                        secondary: '#b3c3d0',
                        accent: '#93d5e6',
                        error: '#fca5a5',
                        info: '#a6c7ff',
                        success: '#86efac',
                        warning: '#fde047',
                        background: '#121c18',
                        surface: '#1b2822',
                        'surface-light': '#26382f',
                        'on-surface': '#e4eee8',
                        'on-background': '#e4eee8',
                        'draft-ink': '#c0d1c5', 'draft-surface': '#29382f',
                        'due-ink': '#ffd49a', 'due-surface': '#493522',
                        'paid-ink': '#93e6b5', 'paid-surface': '#1c4136',
                        'issued-ink': '#a4d4bc', 'issued-surface': '#223b30',
                        'muted-ink': '#c6d2ca', 'muted-surface': '#2b3530',
                    }
                }
            }
        }
    }
};
