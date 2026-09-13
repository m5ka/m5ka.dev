from base64 import b32encode

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = (
        "Adds an authenticator app as a two-factor device for a user. The device only "
        "becomes active once a code from the app has been entered."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--name", default="Authenticator app", help="A label for the device."
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Remove the user's other devices once this one is confirmed, "
            "e.g. after losing a phone.",
        )

    def handle(self, username, name, replace, **options):
        User = get_user_model()
        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            raise CommandError(f'There is no user called "{username}".')

        # leftovers from a previous run that was never confirmed
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=user, name=name, confirmed=False)

        self.stdout.write(
            "Add this to your authenticator app, either as a link or by typing in the "
            "secret key. Anyone who sees these can generate codes for this account.\n\n"
            f"  Link:   {device.config_url}\n"
            f"  Secret: {b32encode(device.bin_key).decode()}\n"
        )
        token = input("Enter the code the app shows to confirm: ").strip()

        if not device.verify_token(token):
            device.delete()
            raise CommandError(
                "That code didn't match, so nothing was changed. Run the command again."
            )

        with transaction.atomic():
            device.confirmed = True
            device.save()
            if replace:
                TOTPDevice.objects.filter(user=user).exclude(pk=device.pk).delete()

        self.stdout.write(
            self.style.SUCCESS(f'Two-factor authentication is set up for "{username}".')
        )
