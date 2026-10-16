import json
import os
import subprocess
import sys


def inspect_settings(tmp_path, extra=None):
    env_file = tmp_path / ".env"
    env_file.write_text("DJANGO_SECRET_KEY=private-test-key\nDJANGO_ALLOWED_HOSTS=ventisax.pythonanywhere.com\nDJANGO_DEBUG=0\n", encoding="utf-8")
    env = os.environ.copy()
    for name in ("DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_SETTINGS_MODULE"):
        env.pop(name, None)
    env.update(DJANGO_ENV_FILE=str(env_file), **(extra or {}))
    result = subprocess.run([sys.executable, "-c", "from config import production as s; import json; print(json.dumps({'debug':s.DEBUG,'key':s.SECRET_KEY,'hosts':s.ALLOWED_HOSTS,'proxy':s.SECURE_PROXY_SSL_HEADER}))"], env=env, capture_output=True, text=True)
    return result


def test_production_charge_env_et_respecte_variables_existantes(tmp_path):
    result = inspect_settings(tmp_path, {"DJANGO_SECRET_KEY": "external-test-key"})
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values == {"debug": False, "key": "external-test-key", "hosts": ["ventisax.pythonanywhere.com"], "proxy": ["HTTP_X_FORWARDED_PROTO", "https"]}


def test_production_refuse_debug_meme_si_env_demande_activation(tmp_path):
    result = inspect_settings(tmp_path, {"DJANGO_DEBUG": "1"})
    assert result.returncode != 0
    assert "RuntimeError: DEBUG interdit en production" in result.stderr


def test_email_otp_parcours_reel_admin_rejeu_expiration_et_cooldown(tmp_path):
    # Processus isolé : les tests TOTP gardent leur configuration habituelle.
    script = '''
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
import django
django.setup()
from django.conf import settings
settings.DATABASES['default']['NAME'] = os.environ['TEST_DB']
settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
from django.core.management import call_command
call_command('migrate', verbosity=0)
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_email.models import EmailDevice
from django.test import Client
from django.core import mail
from django.utils import timezone
from datetime import timedelta
user = get_user_model().objects.create_superuser('owner', 'owner@example.com', 'A-strong-test-password-42')
device = EmailDevice.objects.create(user=user, name='default', confirmed=True)
client = Client()
client.get('/account/login/')
response = client.post('/account/login/', {'login_view-current_step':'auth', 'auth-username':'owner', 'auth-password':'A-strong-test-password-42'})
assert response.status_code == 200
assert client.get('/admin/').status_code == 302
assert len(mail.outbox) == 1
assert mail.outbox[0].to == ['owner@example.com']
device.refresh_from_db()
token = device.token
assert token in mail.outbox[0].body
device.generate_challenge()
assert len(mail.outbox) == 1
response = client.post('/account/login/', {'login_view-current_step':'token','token-otp_token':token})
assert response.status_code == 302
assert client.get('/admin/').status_code == 200
device.refresh_from_db()
assert not device.verify_token(token)
device.throttle_reset()
device.cooldown_reset()
device.generate_challenge()
device.valid_until = timezone.now() - timedelta(seconds=1)
device.save()
assert not device.verify_token(device.token)
print('EMAIL_FLOW_OK')
'''
    env = os.environ.copy()
    env.update(DJANGO_EMAIL_OTP="1", DJANGO_DEBUG="1", TEST_DB=str(tmp_path / "db.sqlite3"))
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "EMAIL_FLOW_OK" in result.stdout


def test_production_ajoute_une_empreinte_aux_fichiers_statiques(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DJANGO_SECRET_KEY=private-test-key\nDJANGO_ALLOWED_HOSTS=ventisax.pythonanywhere.com\nDJANGO_DEBUG=0\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_SETTINGS_MODULE")}
    env["DJANGO_ENV_FILE"] = str(env_file)
    result = subprocess.run([sys.executable, "-c", "from config import production as s; print(s.STORAGES['staticfiles']['BACKEND'])"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"


def test_collectstatic_produit_des_noms_avec_empreinte_et_references_a_jour(tmp_path, settings):
    import re
    from django.core.management import call_command
    from django.templatetags.static import static
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"}}
    call_command("collectstatic", interactive=False, verbosity=0)
    css = static("hub/site.css")
    assert re.fullmatch(r"/static/hub/site\.[0-9a-f]{12}\.css", css), css
    content = (tmp_path / css.removeprefix("/static/")).read_text(encoding="utf-8")
    assert re.search(r'url\("fonts/lexend-latin-wght\.[0-9a-f]{12}\.woff2"\)', content)
    assert re.search(r'url\("ventisax-mark\.[0-9a-f]{12}\.svg"\)', content)
    assert re.fullmatch(r"/static/hub/site\.[0-9a-f]{12}\.js", static("hub/site.js"))
