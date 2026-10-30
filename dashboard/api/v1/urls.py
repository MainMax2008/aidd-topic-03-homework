from django.urls import include, path

from .portfolio import PortfolioAPIView
from .router import router

urlpatterns = [
	path("portfolio/", PortfolioAPIView.as_view(), name="portfolio-api"),
	path("", include(router.urls)),
]
