from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View, UpdateView

from .forms import ShareModelForm
from .models import Share, Transaction
from .services.graph import get_graph
from .services.portfolio import (
    PortfolioError,
    buy_share,
    get_or_create_portfolio,
    get_portfolio_summary,
    sell_share,
)
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(View):
    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, id=pk)

        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": get_graph(share), "share": share},
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление задачи"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")


class PortfolioView(LoginRequiredMixin, View):
    """Виртуальный инвестиционный портфель"""

    login_url = reverse_lazy("user:auth")

    @staticmethod
    def get(request):
        portfolio = get_or_create_portfolio(request.user)
        context = get_portfolio_summary(portfolio)
        return render(request, "dashboard/portfolio.html", context)

    @staticmethod
    def post(request):
        portfolio = get_or_create_portfolio(request.user)
        action = request.POST.get("action")
        quantity = request.POST.get("quantity")
        share = get_object_or_404(Share, id=request.POST.get("share_id"))

        try:
            if action == "buy":
                buy_share(request.user, share, quantity)
                messages.success(
                    request,
                    f"Куплено {quantity} акций {share.ticker} "
                    f"по цене {share.last_price}.",
                )
            elif action == "sell":
                sell_share(request.user, share, quantity)
                messages.success(
                    request,
                    f"Продано {quantity} акций {share.ticker} "
                    f"по цене {share.last_price}.",
                )
            else:
                messages.error(request, "Неизвестное действие.")
        except PortfolioError as error:
            messages.error(request, str(error))

        return redirect("dashboard:portfolio")


class PortfolioTransactionsView(LoginRequiredMixin, ListView):
    """История сделок пользователя"""

    login_url = reverse_lazy("user:auth")
    model = Transaction
    template_name = "dashboard/portfolio_transactions.html"
    context_object_name = "transaction_list"
    paginate_by = 50

    def get_queryset(self):
        return Transaction.objects.filter(
            portfolio__user=self.request.user
        ).select_related("share", "portfolio")
