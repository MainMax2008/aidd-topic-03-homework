from django.contrib import admin

from dashboard.models import Portfolio, PortfolioPosition, Share, Transaction


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )


class PortfolioPositionInline(admin.TabularInline):
    model = PortfolioPosition
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "created_at")
    search_fields = ("user__username", "user__email")
    inlines = (PortfolioPositionInline,)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "portfolio",
        "share",
        "transaction_type",
        "quantity",
        "price",
        "total_amount",
        "created_at",
    )
    list_filter = ("transaction_type",)
