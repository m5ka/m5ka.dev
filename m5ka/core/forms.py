from django import forms
from django.utils.translation import gettext_lazy as _
from django_otp.forms import OTPTokenForm


class VerifyTwoFactorForm(OTPTokenForm):
    """
    django-otp's token form, which only offers the user's own confirmed devices and
    throttles failed attempts. The device choice is hidden when there's only one.
    """

    def __init__(self, user, request=None, *args, **kwargs):
        super().__init__(user, request, *args, **kwargs)
        # TOTP devices have no challenge to send
        del self.fields["otp_challenge"]

        device = self.fields["otp_device"]
        device.label = _("Device")
        if len(device.choices) == 1:
            device.initial = device.choices[0][0]
            device.widget = forms.HiddenInput()

        token = self.fields["otp_token"]
        token.label = _("Code")
        token.required = True
        token.widget.attrs.update(
            {"autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True}
        )

    @property
    def has_devices(self):
        return bool(self.fields["otp_device"].choices)
