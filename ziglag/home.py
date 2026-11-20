import datetime

from quart import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
)
from quart_security import current_user, hash_password
from quart_security.proxies import _security
from sqlalchemy import func, select
from stk.user.models import Role, User

home = Blueprint("home", __name__)


async def user_count():
    return (await g.db_session.execute(select(func.count()).select_from(User))).scalar()


@home.get("/")
async def index():
    if current_user.is_authenticated:
        return redirect("/dashboard/")
    # If no users exist, redirect to first-run setup
    if await user_count() == 0:
        return redirect("/setup")
    return redirect("/login")


@home.route("/setup", methods=["GET", "POST"])
async def setup():
    if await user_count() > 0:
        return redirect("/login")

    if request.method == "POST":
        form = await request.form
        email = form.get("email", "").strip()
        password = form.get("password", "").strip()
        name = form.get("name", "").strip()

        min_len = current_app.config.get("SECURITY_PASSWORD_LENGTH_MIN", 12)
        if not email or not password or len(password) < min_len:
            await flash(
                f"Email and password (min {min_len} chars) are required.", "error"
            )
            return redirect("/setup")

        # Create admin role
        role = (
            await g.db_session.execute(select(Role).where(Role.name == "admin"))
        ).scalar_one_or_none()
        if not role:
            role = Role(name="admin", description="Administrator")
            g.db_session.add(role)
            await g.db_session.flush()

        user = User(
            email=email,
            name=name or "Admin",
            password=hash_password(password),
            active=True,
            confirmed_at=datetime.datetime.now(),
        )
        user.roles = [role]
        g.db_session.add(user)
        await g.db_session.commit()

        # Log user in
        await _security.login_user(user)
        return redirect("/dashboard/")

    return await render_template("setup.html")
