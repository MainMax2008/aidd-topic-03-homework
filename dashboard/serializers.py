from rest_framework import serializers

from dashboard.models import PortfolioTransaction, Position


class PortfolioTransactionSerializer(serializers.ModelSerializer):
    share_id = serializers.IntegerField(read_only=True)
    ticker = serializers.CharField(source="share.ticker", read_only=True)
    share_name = serializers.CharField(source="share.name", read_only=True)

    class Meta:
        model = PortfolioTransaction
        fields = (
            "id",
            "transaction_type",
            "share_id",
            "ticker",
            "share_name",
            "quantity",
            "price",
            "total_amount",
            "created_at",
        )


class TransactionSerializer(PortfolioTransactionSerializer):
    """Backward-compatible name for transaction serialization."""


class PositionSerializer(serializers.ModelSerializer):
    share_id = serializers.IntegerField(source="share.id", read_only=True)
    ticker = serializers.CharField(source="share.ticker", read_only=True)
    name = serializers.CharField(source="share.name", read_only=True)
    current_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True, read_only=True
    )
    market_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, allow_null=True, read_only=True
    )
    pnl = serializers.DecimalField(
        max_digits=14, decimal_places=2, allow_null=True, read_only=True
    )
    pnl_percent = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True, read_only=True
    )

    class Meta:
        model = Position
        fields = (
            "share_id",
            "ticker",
            "name",
            "quantity",
            "average_buy_price",
            "current_price",
            "market_value",
            "pnl",
            "pnl_percent",
        )


class PortfolioSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_shares_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_portfolio_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_invested = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_pnl = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_pnl_percent = serializers.DecimalField(max_digits=12, decimal_places=2)
    prices_complete = serializers.BooleanField()
    unpriced_positions = serializers.IntegerField()
    positions = PositionSerializer(many=True)
    recent_transactions = PortfolioTransactionSerializer(many=True)

    # Compatibility aliases retained for existing API clients.
    market_value = serializers.DecimalField(
        source="total_shares_value", max_digits=14, decimal_places=2
    )
    total_assets = serializers.DecimalField(
        source="total_portfolio_value", max_digits=14, decimal_places=2
    )
    transactions = PortfolioTransactionSerializer(
        source="recent_transactions", many=True
    )


class PortfolioTradeSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("BUY", "SELL"))
    share_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
