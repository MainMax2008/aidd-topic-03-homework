from django.test import TestCase
from django.urls import reverse


class UserFormValidationTests(TestCase):
    def test_registration_renders_field_errors(self):
        response = self.client.post(reverse("user:registration"), {"email": "bad"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("password1", response.context["form"].errors)
        self.assertIn("password2", response.context["form"].errors)

    def test_login_renders_field_errors(self):
        response = self.client.post(reverse("user:auth"), {"email": "bad"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("password", response.context["form"].errors)