from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import INITIAL_BALANCE, Portfolio, PortfolioPosition, Share, Transaction
from dashboard.services.portfolio import (
    PortfolioError,
    buy_share,
    get_portfolio_summary,
    sell_share,
)


class DashboardTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )

        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )

        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "usd",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    def test_share_list_html(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_list(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple_share = response.json().get("results")[0]
        self.assertEqual(apple_share["id"], self.apple_share.id)
        self.assertEqual(apple_share["figi"], self.apple_share.figi)
        self.assertEqual(apple_share["isin"], self.apple_share.isin)
        self.assertEqual(apple_share["name"], self.apple_share.name)
        self.assertEqual(apple_share["ticker"], self.apple_share.ticker)
        self.assertEqual(apple_share["currency"], self.apple_share.currency)

    def test_share_detail(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.get(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_detail_invalid(self):
        response = self.client.get("/api/v1/shares/2/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_update(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "id": share_detail["id"],
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": f"{self.apple_share.name}_test",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["figi"], self.apple_share.figi)
        self.assertEqual(body["name"], f"{self.apple_share.name}_test")

    def test_share_update_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "figi": self.apple_share.figi,
                "name": f"{self.apple_share.name}_test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_create(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["figi"], self.second_company["figi"])
        self.assertEqual(body["name"], self.second_company["name"])
        self.assertEqual(body["ticker"], self.second_company["ticker"])

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 2)

    def test_share_create_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.delete(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/v1/shares/3/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_create_anonymous_denied(self):
        """Неавторизованный пользователь не может создавать акции."""
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_share_update_anonymous_denied(self):
        """Неавторизованный пользователь не может изменять акции."""
        response = self.client.put(
            f"/api/v1/shares/{self.apple_share.id}/",
            {"name": "Hacked"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class PortfolioTests(TestCase):
    """Тесты виртуального инвестиционного портфеля"""

    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="portfolio@example.com",
            email="portfolio@example.com",
            password="testpass123",
        )
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )
        # Портфель создается сигналом при создании пользователя
        self.portfolio = Portfolio.objects.get(user=self.user)

    def test_portfolio_created_on_user_creation(self):
        """Портфель создается автоматически с начальным балансом"""
        self.assertTrue(Portfolio.objects.filter(user=self.user).exists())
        self.assertEqual(self.portfolio.balance, INITIAL_BALANCE)
        self.assertEqual(self.portfolio.balance, Decimal("100000.00"))


    def test_buy_success(self):
        """Успешная покупка списывает сумму с баланса и создает позицию"""
        buy_share(self.user, self.apple_share, 10)

        self.portfolio.refresh_from_db()
        # 100000.00 - 10 * 100.50 = 98995.00
        self.assertEqual(self.portfolio.balance, Decimal("98995.00"))

        position = PortfolioPosition.objects.get(
            portfolio=self.portfolio, share=self.apple_share
        )
        self.assertEqual(position.quantity, 10)
        self.assertEqual(position.average_price, Decimal("100.50"))

        transaction = Transaction.objects.get(portfolio=self.portfolio)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.BUY)
        self.assertEqual(transaction.quantity, 10)
        self.assertEqual(transaction.total_amount, Decimal("1005.00"))

    def test_buy_insufficient_funds(self):
        """Покупка при нехватке средств вызывает ошибку и не меняет баланс"""
        with self.assertRaises(PortfolioError):
            buy_share(self.user, self.apple_share, 1000)

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.balance, INITIAL_BALANCE)
        self.assertFalse(
            PortfolioPosition.objects.filter(portfolio=self.portfolio).exists()
        )
        self.assertFalse(
            Transaction.objects.filter(portfolio=self.portfolio).exists()
        )


    def test_buy_recalculates_average_price(self):
        """При докупке пересчитывается средняя цена позиции"""
        buy_share(self.user, self.apple_share, 10)  # по 100.50

        self.apple_share.last_price = 120.50
        self.apple_share.save(update_fields=["last_price"])
        buy_share(self.user, self.apple_share, 10)  # по 120.50

        position = PortfolioPosition.objects.get(
            portfolio=self.portfolio, share=self.apple_share
        )
        self.assertEqual(position.quantity, 20)
        # (10 * 100.50 + 10 * 120.50) / 20 = 110.50
        self.assertEqual(position.average_price, Decimal("110.50"))

        self.portfolio.refresh_from_db()
        # 100000.00 - 1005.00 - 1205.00 = 97790.00
        self.assertEqual(self.portfolio.balance, Decimal("97790.00"))

    def test_sell_success(self):
        """Успешная продажа пополняет баланс и уменьшает позицию"""
        buy_share(self.user, self.apple_share, 10)

        self.apple_share.last_price = 110.00
        self.apple_share.save(update_fields=["last_price"])
        sell_share(self.user, self.apple_share, 5)

        self.portfolio.refresh_from_db()
        # 98995.00 + 5 * 110.00 = 99545.00
        self.assertEqual(self.portfolio.balance, Decimal("99545.00"))

        position = PortfolioPosition.objects.get(
            portfolio=self.portfolio, share=self.apple_share
        )
        self.assertEqual(position.quantity, 5)
        # Средняя цена покупки при продаже не меняется
        self.assertEqual(position.average_price, Decimal("100.50"))

        sell_transaction = Transaction.objects.get(
            portfolio=self.portfolio,
            transaction_type=Transaction.TransactionType.SELL,
        )
        self.assertEqual(sell_transaction.quantity, 5)
        self.assertEqual(sell_transaction.total_amount, Decimal("550.00"))


    def test_sell_more_than_available(self):
        """Продажа большего объема, чем есть в наличии, вызывает ошибку"""
        buy_share(self.user, self.apple_share, 5)

        with self.assertRaises(PortfolioError):
            sell_share(self.user, self.apple_share, 10)

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.balance, Decimal("99497.50"))

        position = PortfolioPosition.objects.get(
            portfolio=self.portfolio, share=self.apple_share
        )
        self.assertEqual(position.quantity, 5)
        # Ошибка не создает сделку продажи
        self.assertFalse(
            Transaction.objects.filter(
                portfolio=self.portfolio,
                transaction_type=Transaction.TransactionType.SELL,
            ).exists()
        )

    def test_buy_non_positive_quantity(self):
        """Покупка нулевого или отрицательного количества запрещена"""
        with self.assertRaises(PortfolioError):
            buy_share(self.user, self.apple_share, 0)
        with self.assertRaises(PortfolioError):
            buy_share(self.user, self.apple_share, -3)

    def test_sell_non_positive_quantity(self):
        """Продажа нулевого или отрицательного количества запрещена"""
        buy_share(self.user, self.apple_share, 5)
        with self.assertRaises(PortfolioError):
            sell_share(self.user, self.apple_share, 0)

    def test_full_sell_removes_position(self):
        """При полной продаже позиция удаляется"""
        buy_share(self.user, self.apple_share, 5)
        sell_share(self.user, self.apple_share, 5)

        self.assertFalse(
            PortfolioPosition.objects.filter(
                portfolio=self.portfolio, share=self.apple_share
            ).exists()
        )
        self.portfolio.refresh_from_db()
        # Баланс возвращается к начальному значению
        self.assertEqual(self.portfolio.balance, INITIAL_BALANCE)


    def test_portfolio_summary(self):
        """Сводка по портфелю считает стоимость и PnL корректно"""
        buy_share(self.user, self.apple_share, 10)

        self.portfolio.refresh_from_db()
        summary = get_portfolio_summary(self.portfolio)
        # Стоимость позиций: 10 * 100.50 = 1005.00
        self.assertEqual(summary["positions_value"], Decimal("1005.00"))
        # Общая стоимость: 98995.00 + 1005.00 = 100000.00
        self.assertEqual(summary["total_value"], Decimal("100000.00"))
        # PnL при цене покупки равной текущей цене: 0
        self.assertEqual(summary["total_pnl"], Decimal("0.00"))

        # Цена выросла - PnL положительный
        self.apple_share.last_price = 150.00
        self.apple_share.save(update_fields=["last_price"])
        self.portfolio.refresh_from_db()
        summary = get_portfolio_summary(self.portfolio)
        # Стоимость позиций: 10 * 150.00 = 1500.00, PnL: 1500 - 1005 = 495.00
        self.assertEqual(summary["positions_value"], Decimal("1500.00"))
        self.assertEqual(summary["total_value"], Decimal("100495.00"))
        self.assertEqual(summary["total_pnl"], Decimal("495.00"))

    def test_portfolio_view_requires_login(self):
        """Неавторизованный пользователь перенаправляется на авторизацию"""
        response = self.client.get(reverse("dashboard:portfolio"))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(reverse("user:auth"), response.url)

    def test_portfolio_view_renders(self):
        """Авторизованный пользователь видит портфель"""
        buy_share(self.user, self.apple_share, 10)
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:portfolio"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Мой портфель")
        self.assertContains(response, "AAPL")

    def test_portfolio_buy_via_view(self):
        """Покупка через POST-запрос представления"""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard:portfolio"),
            {"action": "buy", "share_id": self.apple_share.id, "quantity": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.portfolio.refresh_from_db()
        # 100000.00 - 2 * 100.50 = 99799.00
        self.assertEqual(self.portfolio.balance, Decimal("99799.00"))
        self.assertTrue(
            PortfolioPosition.objects.filter(
                portfolio=self.portfolio, share=self.apple_share, quantity=2
            ).exists()
        )

    def test_portfolio_sell_via_view_error_message(self):
        """Ошибка продажи через представление показывает сообщение"""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("dashboard:portfolio"),
            {"action": "sell", "share_id": self.apple_share.id, "quantity": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        messages_list = list(response.wsgi_request._messages)
        self.assertTrue(any(message.level_tag == "error" for message in messages_list))

    def test_portfolio_transactions_view(self):
        """История сделок отображает только сделки пользователя"""
        buy_share(self.user, self.apple_share, 10)

        other_user = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        other_share = Share.objects.create(
            figi="BBG000B9XRY6",
            isin="US0378331006",
            name="Other",
            ticker="OTHR",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e40",
            last_price=10.00,
            is_trend_high=False,
        )
        buy_share(other_user, other_share, 3)

        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:portfolio_transactions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.context["transaction_list"]), 1)
        self.assertContains(response, "AAPL")

