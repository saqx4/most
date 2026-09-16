from django.test import TestCase

from apps.core.models import Company, Role, User


class CompanyModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Test Co', base_currency='USD')

    def test_create_company(self):
        self.assertEqual(self.company.name, 'Test Co')
        self.assertTrue(self.company.is_active)

    def test_str(self):
        self.assertEqual(str(self.company), 'Test Co')

    def test_default_values(self):
        self.assertFalse(self.company.is_default)
        self.assertTrue(self.company.is_active)
        self.assertEqual(self.company.base_currency, 'USD')


class RoleModelTest(TestCase):
    def test_create_role(self):
        role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.assertEqual(role.code, 'admin')
        self.assertEqual(str(role), 'Admin')

    def test_role_choices(self):
        self.assertEqual(Role.RoleChoices.ADMIN, 'admin')
        self.assertEqual(Role.RoleChoices.MANAGER, 'manager')
        self.assertEqual(Role.RoleChoices.ACCOUNTANT, 'accountant')


class UserModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='testuser', password='pass1234',
            company=self.company, role=self.role,
        )

    def test_create_user(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.company, self.company)

    def test_str(self):
        self.assertEqual(str(self.user), 'testuser')

    def test_is_admin_property(self):
        self.assertTrue(self.user.is_admin)

    def test_can_edit_property(self):
        self.assertTrue(self.user.can_edit)

    def test_has_module_access_admin(self):
        self.assertTrue(self.user.has_module_access('accounting'))

    def test_user_without_role(self):
        u = User.objects.create_user(username='norole', password='pass1234')
        self.assertFalse(u.is_admin)
        self.assertFalse(u.has_module_access('hr'))
