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


def _trade_view(request, trade_function, action, share_id=None):
    trade_data = request.POST.copy()
    if share_id is not None:
        trade_data["share"] = share_id
    form = PortfolioTradeForm(trade_data)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        destination = (
            redirect("dashboard:detail", pk=share_id)
            if share_id is not None
            else redirect("dashboard:portfolio")
        )
        return destination

    try:
        trade_function(
            request.user,
            share_id or form.cleaned_data["share"].pk,
            form.cleaned_data["quantity"],
        )
    except ValidationError as error:
        for error_message in error.messages:
            messages.error(request, error_message)
    else:
        messages.success(request, f"Операция: {action} успешно выполнена.")
    if share_id is not None:
        return redirect("dashboard:detail", pk=share_id)
    return redirect("dashboard:portfolio")


@login_required(login_url="user:auth")
@require_POST
def portfolio_buy_view(request, share_id=None):
    return _trade_view(request, buy_share, "покупка", share_id)


@login_required(login_url="user:auth")
@require_POST
def portfolio_sell_view(request, share_id=None):
    return _trade_view(request, sell_share, "продажа", share_id)
