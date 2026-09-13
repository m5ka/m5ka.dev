from django.db import migrations


def remove_enable_2fa_permission(apps, schema_editor):
    # created by wagtail-2fa, which has been replaced by m5ka.core's own 2FA check
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(
        content_type__app_label="wagtailadmin", codename="enable_2fa"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('m5ka_core', '0009_alter_blogpost_body_alter_page_body'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('wagtailadmin', '0006_formstate'),
    ]

    operations = [
        migrations.RunPython(remove_enable_2fa_permission, migrations.RunPython.noop),
    ]
