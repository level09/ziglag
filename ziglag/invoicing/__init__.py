def init_app(app):
    from ziglag.adopt import adopt_stk16
    from ziglag.backup_cli import backup
    from ziglag.home import home
    from ziglag.invoicing.public import public_invoice
    from ziglag.invoicing.views import dashboard, invoicing

    app.register_blueprint(home)
    app.register_blueprint(invoicing)
    app.register_blueprint(public_invoice)
    # stk's portal blueprint owns /dashboard/ and its login requirement.
    app.view_functions["portal.dashboard"] = dashboard
    app.cli.add_command(backup)
    app.cli.add_command(adopt_stk16)
    # The whole sidebar: layout.html renders app.navigation alone, without stk's
    # Account section (those pages are in the avatar menu) or its Jobs page.
    app.navigation.extend(
        [
            {
                "title": "Dashboard",
                "icon": "ti ti-layout-dashboard",
                "to": "/dashboard",
            },
            {"title": "Invoices", "icon": "ti ti-file-invoice", "to": "/invoices"},
            {"title": "Customers", "icon": "ti ti-users", "to": "/clients"},
            {"title": "Reports", "icon": "ti ti-chart-bar", "to": "/reports"},
            {"heading": "Settings"},
            {
                "title": "Business settings",
                "icon": "ti ti-settings",
                "to": "/settings/business",
            },
            {"heading": "Administration", "role": "admin"},
            {
                "title": "Users and roles",
                "icon": "ti ti-users-group",
                "role": "admin",
                "children": [
                    {"title": "Users", "icon": "ti ti-user", "to": "/users"},
                    {"title": "Roles", "icon": "ti ti-shield", "to": "/roles"},
                ],
            },
            {
                "title": "Activity log",
                "icon": "ti ti-history",
                "to": "/activities",
                "role": "admin",
            },
        ]
    )
