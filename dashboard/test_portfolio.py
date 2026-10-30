from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import (
    Portfolio,
    PortfolioTransaction,
    Position,
    Share,
)
from dashboard.portfolio_service import (
    buy_share,
    get_portfolio_summary,
    sell_share,
)


def create_share(ticker="TEST", last_price=10.5):
    return Share.objects.create(
        figi=f"FIGI-{ticker}",
        isin=f"ISIN-{ticker}",
        name=f"Share {ticker}",
        ticker=ticker,
        currency="rub",
        uid=f"UID-{ticker}",
        last_price=last_price,
    )


class PortfolioServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="portfolio-user", password="password"
        )
        self.share = create_share()

    def test_buy_creates_portfolio_and_updates_weighted_average(self):
        buy_share(self.user, self.share.pk, 2)
        self.share.last_price = 12.5
        self.share.save(update_fields=("last_price",))
        buy_share(self.user, self.share.pk, 2)

        portfolio = Portfolio.objects.get(user=self.user)
        position = Position.objects.get(portfolio=portfolio, share=self.share)
        self.assertEqual(portfolio.balance, Decimal("99954.00"))
        self.assertEqual(position.quantity, 4)
        self.assertEqual(position.average_buy_price, Decimal("11.50"))
        self.assertEqual(PortfolioTransaction.objects.count(), 2)

    def test_buy_rejects_insufficient_balance_without_partial_changes(self):
        self.share.last_price = 200000
        self.share.save(update_fields=("last_price",))

        with self.assertRaises(ValidationError):
            buy_share(self.user, self.share.pk, 1)

        portfolio = Portfolio.objects.get(user=self.user)
        self.assertEqual(portfolio.balance, Decimal("100000.00"))
        self.assertFalse(Position.objects.filter(portfolio=portfolio).exists())
        self.assertFalse(PortfolioTransaction.objects.exists())

    def test_sell_credits_cash_and_removes_empty_position(self):
        buy_share(self.user, self.share.pk, 2)
        self.share.last_price = 12.5
        self.share.save(update_fields=("last_price",))
        sell_share(self.user, self.share.pk, 2)

        portfolio = Portfolio.objects.get(user=self.user)
        self.assertEqual(portfolio.balance, Decimal("100004.00"))
        self.assertFalse(Position.objects.filter(portfolio=portfolio).exists())
        self.assertEqual(PortfolioTransaction.objects.count(), 2)

    def test_sell_rejects_quantity_above_position(self):
        with self.assertRaises(ValidationError):
            sell_share(self.user, self.share.pk, 1)

    def test_buy_rejects_non_ruble_share_without_currency_conversion(self):
        self.share.currency = "usd"
        self.share.save(update_fields=("currency",))

        with self.assertRaises(ValidationError):
            buy_share(self.user, self.share.pk, 1)

    def test_summary_reports_unavailable_prices(self):
        buy_share(self.user, self.share.pk, 1)
        self.share.last_price = None
        self.share.save(update_fields=("last_price",))

        summary = get_portfolio_summary(self.user)

        self.assertFalse(summary["prices_complete"])
        self.assertEqual(summary["unpriced_positions"], 1)
        self.assertIsNone(summary["positions"][0]["market_value"])


class PortfolioWebTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="portfolio-web-user", password="test-password"
        )
        self.share = create_share("WEB", 10.5)

    def test_portfolio_requires_login(self):
        response = self.client.get(reverse("dashboard:portfolio"))
        self.assertEqual(response.status_code, 302)
        expected_url = f"{reverse('user:auth')}?next={reverse('dashboard:portfolio')}"
        self.assertRedirects(response, expected_url)

    def test_portfolio_displays_summary_and_positions(self):
        self.client.force_login(self.user)
        buy_share(self.user, self.share.pk, 2)

        response = self.client.get(reverse("dashboard:portfolio"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Общий капитал")
        self.assertContains(response, "WEB")
        self.assertContains(response, "21.00")

    def test_share_trade_routes_buy_and_sell(self):
        self.client.force_login(self.user)
        buy_url = reverse("dashboard:portfolio_buy", args=[self.share.pk])
        sell_url = reverse("dashboard:portfolio_sell", args=[self.share.pk])

        buy_response = self.client.post(buy_url, {"quantity": 2})

        self.assertRedirects(
            buy_response,
            reverse("dashboard:detail", args=[self.share.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(Position.objects.get().quantity, 2)

        sell_response = self.client.post(sell_url, {"quantity": 1})

        self.assertRedirects(
            sell_response,
            reverse("dashboard:detail", args=[self.share.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(Position.objects.get().quantity, 1)
        self.assertEqual(PortfolioTransaction.objects.count(), 2)


class PortfolioApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="portfolio-api-user", password="password"
        )
        self.share = create_share("API", 15.25)
        self.url = "/api/v1/portfolio/"

    def test_portfolio_api_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_read_and_trade(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance"], "100000.00")

        response = self.client.post(
            self.url,
            {"action": "BUY", "share_id": self.share.pk, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["positions"][0]["quantity"], 2)
