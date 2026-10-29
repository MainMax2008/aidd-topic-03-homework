from django.urls import include, path

from dashboard.views import (
    PortfolioTransactionsView,
    PortfolioView,
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
)

app_name = "dashboard"

urlpatterns = [
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path(
        "portfolio/transactions/",
        PortfolioTransactionsView.as_view(),
        name="portfolio_transactions",
    ),
    path("api/", include("dashboard.api.urls")),
]
