from django import forms

from dashboard.models import Share


class PortfolioTradeForm(forms.Form):
    share = forms.ModelChoiceField(queryset=Share.objects.none(), label="Акция")
    quantity = forms.IntegerField(min_value=1, label="Количество")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["share"].queryset = Share.objects.order_by("ticker")
        self.fields["share"].widget.attrs["class"] = "form-select"
        self.fields["quantity"].widget.attrs.update(
            {"class": "form-control", "min": 1, "step": 1}
        )
