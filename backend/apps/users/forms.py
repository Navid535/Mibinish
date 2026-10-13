from django import forms


class ActivatePremiumForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    days = forms.IntegerField(
        min_value=1,
        label="Days to grant/extend",
        help_text="If a user already has active premium, this is added on top of their current expiry.",
    )
