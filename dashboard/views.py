from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View, UpdateView
from django.views.decorators.http import require_POST

from .forms import ShareModelForm
from .models import Share
from django.contrib.auth.mixins import UserPassesTestMixin
from .portfolio_forms import PortfolioTradeForm
from .portfolio_service import buy_share, get_portfolio_summary, sell_share


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
        from .services.graph import get_graph

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


def _portfolio_context(user, buy_form=None, sell_form=None):
    context = get_portfolio_summary(user)
    context["buy_form"] = buy_form or PortfolioTradeForm()
    context["sell_form"] = sell_form or PortfolioTradeForm()
    return context


@login_required(login_url="user:auth")
def portfolio_view(request):
    return render(
        request,
        "dashboard/portfolio.html",
        _portfolio_context(request.user),
    )


def _trade_view(request, trade_function, action):
    form = PortfolioTradeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Проверьте введенные данные сделки.")
        context = _portfolio_context(
            request.user,
            buy_form=form if action == "покупка" else None,
            sell_form=form if action == "продажа" else None,
        )
        return render(request, "dashboard/portfolio.html", context, status=400)

    try:
        trade_function(
            request.user,
            form.cleaned_data["share"].pk,
            form.cleaned_data["quantity"],
        )
    except ValidationError as error:
        for error_message in error.messages:
            messages.error(request, error_message)
    else:
        messages.success(request, f"Операция: {action} успешно выполнена.")
    return redirect("dashboard:portfolio")


@login_required(login_url="user:auth")
@require_POST
def portfolio_buy_view(request):
    return _trade_view(request, buy_share, "покупка")


@login_required(login_url="user:auth")
@require_POST
def portfolio_sell_view(request):
    return _trade_view(request, sell_share, "продажа")
