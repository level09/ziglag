import unittest

import stk
import stk.extensions as ext
from sqlalchemy import select
from stk.user.models import User

from ziglag.app import extensions
from ziglag.settings import Config


class HomeConfig(stk.TestingConfig, Config):
    pass


class HomeRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = stk.Stk("ziglag.app", config=HomeConfig, extensions=extensions)
        async with ext.engine.begin() as conn:
            await conn.run_sync(ext.Base.metadata.create_all)
        self.client = self.app.test_client()

    async def asyncTearDown(self):
        await ext.engine.dispose()

    async def create_admin(self):
        response = await self.client.get("/setup")
        self.assertEqual(response.status_code, 200)
        async with self.client.session_transaction() as cookie:
            csrf = cookie["_csrf_token"]
        return await self.client.post(
            "/setup",
            form={
                "csrf_token": csrf,
                "name": "Owner",
                "email": "owner@example.com",
                "password": "TestPassword123!",
            },
        )

    async def test_root_sends_a_fresh_install_to_setup(self):
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/setup")

    async def test_setup_creates_admin_signs_in_and_closes(self):
        response = await self.create_admin()
        self.assertEqual(response.headers["Location"], "/dashboard/")
        async with ext.async_session_factory() as session:
            user = (await session.execute(select(User))).scalar_one()
        self.assertEqual([role.name for role in user.roles], ["admin"])
        self.assertEqual((await self.client.get("/dashboard/")).status_code, 200)
        self.assertEqual(
            (await self.client.get("/")).headers["Location"], "/dashboard/"
        )
        self.assertEqual(
            (await self.client.get("/setup")).headers["Location"], "/login"
        )

    async def test_root_sends_visitors_to_login_once_a_user_exists(self):
        await self.create_admin()
        visitor = self.app.test_client()
        response = await visitor.get("/")
        self.assertEqual(response.headers["Location"], "/login")

    async def test_setup_post_requires_csrf_token(self):
        response = await self.client.post(
            "/setup",
            form={"email": "owner@example.com", "password": "TestPassword123!"},
        )
        self.assertNotEqual(response.headers.get("Location"), "/dashboard/")
        async with ext.async_session_factory() as session:
            self.assertIsNone((await session.execute(select(User))).first())

    async def test_dashboard_requires_login(self):
        response = await self.client.get("/dashboard/")
        self.assertIn(response.status_code, (302, 401))
