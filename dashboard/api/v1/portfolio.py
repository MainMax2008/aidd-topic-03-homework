from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.portfolio_service import (
    buy_share,
    get_portfolio_summary,
    sell_share,
)
from dashboard.serializers import PortfolioSerializer, PortfolioTradeSerializer


class PortfolioAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        summary = get_portfolio_summary(request.user)
        return Response(PortfolioSerializer(summary).data)

    def post(self, request):
        trade = PortfolioTradeSerializer(data=request.data)
        trade.is_valid(raise_exception=True)
        data = trade.validated_data

        try:
            if data["action"] == "BUY":
                buy_share(request.user, data["share_id"], data["quantity"])
            else:
                sell_share(request.user, data["share_id"], data["quantity"])
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error

        summary = get_portfolio_summary(request.user)
        return Response(PortfolioSerializer(summary).data, status=status.HTTP_200_OK)
