from django.urls import include, path

from dashboard.views import (
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
    portfolio_buy_view,
    portfolio_sell_view,
    portfolio_view,
)

app_name = "dashboard"

urlpatterns = [
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("portfolio/", portfolio_view, name="portfolio"),
    path("portfolio/buy/", portfolio_buy_view, name="portfolio-buy"),
    path("portfolio/sell/", portfolio_sell_view, name="portfolio-sell"),
    path("portfolio/buy/<int:share_id>/", portfolio_buy_view, name="portfolio_buy"),
    path("portfolio/sell/<int:share_id>/", portfolio_sell_view, name="portfolio_sell"),
    path("api/", include("dashboard.api.urls")),
]
