/**
 * ZigLag Navigation Configuration
 */

const stkNavigation = [
  {
    heading: 'Invoicing'
  },
  {
    title: 'Dashboard',
    icon: 'ti ti-dashboard',
    to: '/dashboard'
  },
  {
    title: 'Invoices',
    icon: 'ti ti-file-invoice',
    to: '/invoices'
  },
  {
    title: 'Customers',
    icon: 'ti ti-users',
    to: '/clients'
  },
  {
    title: 'Reports',
    icon: 'ti ti-chart-bar',
    to: '/reports'
  },
  {
    heading: 'Settings'
  },
  {
    title: 'Business settings',
    icon: 'ti ti-settings',
    to: '/settings/business'
  },
  {
    heading: 'Administration',
    role: 'admin'
  },
  {
    title: 'User management',
    icon: 'ti ti-users-group',
    role: 'admin',
    children: [
      {
        title: 'Users',
        icon: 'ti ti-users',
        to: '/users'
      },
      {
        title: 'Roles',
        icon: 'ti ti-shield',
        to: '/roles'
      }
    ]
  },
  {
    title: 'Activity logs',
    icon: 'ti ti-history',
    to: '/activities',
    role: 'admin'
  }
];
