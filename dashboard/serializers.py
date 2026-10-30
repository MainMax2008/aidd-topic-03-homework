from rest_framework import serializers

from dashboard.models import PortfolioTransaction


class TransactionSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source="share.ticker", read_only=True)
    share_name = serializers.CharField(source="share.name", read_only=True)

    class Meta:
        model = PortfolioTransaction
        fields = (
            "id",
            "transaction_type",
            "ticker",
            "share_name",
            "quantity",
            "price",
            "created_at",
        )


class PositionSerializer(serializers.Serializer):
    share_id = serializers.IntegerField(source="share.id")
    ticker = serializers.CharField(source="share.ticker")
    name = serializers.CharField(source="share.name")
    quantity = serializers.IntegerField()
    average_buy_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    market_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, allow_null=True
    )
    pnl = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    pnl_percent = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )


class PortfolioSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    market_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_assets = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_pnl = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_pnl_percent = serializers.DecimalField(max_digits=10, decimal_places=2)
    prices_complete = serializers.BooleanField()
    unpriced_positions = serializers.IntegerField()
    positions = PositionSerializer(many=True)
    transactions = TransactionSerializer(many=True)


class PortfolioTradeSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("BUY", "SELL"))
    share_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
