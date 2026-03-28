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
    title: 'Clients',
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
    title: 'Business Settings',
    icon: 'ti ti-settings',
    to: '/settings/business'
  },
  {
    heading: 'Account'
  },
  {
    title: 'Change Password',
    icon: 'ti ti-key',
    to: '/change'
  },
  {
    heading: 'Administration'
  },
  {
    title: 'User Management',
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
    title: 'Activity Logs',
    icon: 'ti ti-history',
    to: '/activities',
    role: 'admin'
  }
];
