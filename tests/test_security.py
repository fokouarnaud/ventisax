"""Sondes locales de sécurité ; aucune cible externe ni donnée éditoriale réelle."""
import base64
import json
import os
import subprocess
import sys
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone
from django.utils.html import escape
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from tests.factories import configuration, nouvelle, secteur
from tests.test_admin import admin_user, verified_client, login_password

pytestmark = pytest.mark.django_db


def test_session_avant_enrolement_ne_permet_pas_ajout_appareil_attaquant(client, admin_user):
    # Session réelle obtenue avant l'enrôlement dans un autre onglet.
    login_password(client)
    legitimate = TOTPDevice.objects.create(user=admin_user, name="default", confirmed=True)
    response = client.post("/account/two_factor/setup/", {"setup_view-current_step": "welcome"})
    secret = response.context.get("secret_key") if response.context else None
    token = totp(base64.b32decode(secret)) if secret else 123456
    client.post("/account/two_factor/setup/", {
        "setup_view-current_step": "generator", "generator-token": str(token),
    })
    assert client.get("/admin/hub/nouvelle/").status_code == 302
    assert list(TOTPDevice.objects.filter(user=admin_user).values_list("pk", flat=True)) == [legitimate.pk]


def test_enrolement_en_cours_reverifie_appareil_au_post_final(client, admin_user):
    login_password(client)
    response = client.post("/account/two_factor/setup/", {"setup_view-current_step": "welcome"})
    secret = response.context["secret_key"]
    legitimate = TOTPDevice.objects.create(user=admin_user, name="autre-onglet", confirmed=True)
    response = client.post("/account/two_factor/setup/", {
        "setup_view-current_step": "generator", "generator-token": str(totp(base64.b32decode(secret))),
    })
    assert response.status_code == 403
    assert TOTPDevice.objects.filter(user=admin_user).count() == 1
    assert client.get("/admin/").status_code == 302
    assert TOTPDevice.objects.get(pk=legitimate.pk).confirmed


def test_enrolement_initial_change_session_a_elevation_otp(client, admin_user):
    login_password(client)
    response = client.post("/account/two_factor/setup/", {"setup_view-current_step": "welcome"})
    secret = response.context["secret_key"]
    old_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    response = client.post("/account/two_factor/setup/", {
        "setup_view-current_step": "generator", "generator-token": str(totp(base64.b32decode(secret))),
    })
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 200
    stolen = Client()
    stolen.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
    assert stolen.get("/admin/").status_code == 302
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != old_cookie


def test_connexion_otp_change_session_et_ne_stocke_pas_mot_de_passe(client, admin_user):
    device = TOTPDevice.objects.create(user=admin_user, name="default", confirmed=True)
    login_password(client)
    old_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    stored = Session.objects.get(session_key=old_cookie).get_decoded()
    assert "A-strong-test-password-42" not in repr(stored)
    response = client.post("/account/login/", {"login_view-current_step": "token",
        "token-otp_token": str(totp(device.bin_key)).zfill(6)})
    assert response.status_code == 302
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != old_cookie
    stolen = Client()
    stolen.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
    assert stolen.get("/admin/").status_code == 302


def test_parametres_sans_opt_in_ne_demarrent_pas_en_debug():
    env = os.environ.copy()
    env.pop("DJANGO_DEBUG", None)
    env.pop("DJANGO_SECRET_KEY", None)
    result = subprocess.run([sys.executable, "-c", "import config.settings"],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_production_https_hsts_et_cookies_securises():
    env = os.environ.copy()
    env.pop("DJANGO_DEBUG", None)
    env["DJANGO_SECRET_KEY"] = "configuration-synthetique-de-test-" * 3
    env["DJANGO_ALLOWED_HOSTS"] = "ventisax.example.invalid"
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    code = """
import json, django
django.setup()
from django.conf import settings
from django.test import Client
c = Client()
http = c.get('/', HTTP_HOST='ventisax.example.invalid')
https = c.get('/', secure=True, HTTP_HOST='ventisax.example.invalid')
print(json.dumps(dict(debug=settings.DEBUG, session_secure=settings.SESSION_COOKIE_SECURE,
    csrf_secure=settings.CSRF_COOKIE_SECURE, redirect=http.status_code, location=http['Location'],
    hsts=https['Strict-Transport-Security'])))
"""
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    policy = json.loads(result.stdout)
    assert policy["debug"] is False
    assert policy["session_secure"] and policy["csrf_secure"]
    assert policy["redirect"] == 301
    assert policy["location"] == "https://ventisax.example.invalid/"
    assert "max-age=31536000" in policy["hsts"]


def test_duree_session_admin_limitee(verified_client):
    verified_client.get("/admin/")
    stored = Session.objects.get(session_key=verified_client.session.session_key)
    assert stored.expire_date <= timezone.now() + timedelta(minutes=31)
    cookie = verified_client.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert not cookie["expires"]  # cookie de session du navigateur


@pytest.mark.parametrize("payload", ["' OR 1=1 --", "'; DROP TABLE hub_nouvelle; --", "\" OR \"1\"=\"1"])
def test_injection_sql_recherche_admin_et_filtre_public(verified_client, payload):
    configuration()
    s = secteur(publie=True)
    n = nouvelle(publie=True)
    response = verified_client.get("/admin/hub/nouvelle/", {"q": payload})
    assert response.status_code == 200
    assert response.context["cl"].result_count == 0
    response = verified_client.get("/fr/nouvelles/", {"secteur": payload})
    assert response.status_code == 404
    assert type(n).objects.get(pk=n.pk).titre_fr == "Formation réelle"
    assert type(s).objects.get(pk=s.pk).publie


@pytest.mark.parametrize("payload", ["' OR 1=1 --", "owner' --", "'; DROP TABLE auth_user; --"])
def test_injection_sql_connexion_ne_cree_pas_session_authentifiee(client, admin_user, payload):
    client.get("/account/login/")
    response = client.post("/account/login/", {"login_view-current_step": "auth",
        "auth-username": payload, "auth-password": "invalide"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert client.get("/admin/").status_code == 302
    assert get_user_model().objects.get(pk=admin_user.pk).username == "owner"


@pytest.mark.parametrize("payload", ['<script>alert("xss")</script>', '<img src=x onerror="alert(1)">',
                                   '\"><svg onload="alert(1)">'])
def test_xss_stocke_public_admin_et_recherche(verified_client, payload):
    configuration(identite_fr=payload, presentation_en=payload)
    n = nouvelle(titre_fr=payload, titre_en=payload, corps_fr=payload, corps_en=payload, publie=True)
    for path in ["/fr/", "/en/", "/fr/nouvelles/formation/", "/en/nouvelles/formation-en/",
                 "/admin/hub/nouvelle/", f"/admin/hub/nouvelle/{n.pk}/change/"]:
        response = verified_client.get(path)
        assert response.status_code == 200
        assert payload.encode() not in response.content
        assert str(escape(payload)).encode() in response.content
    response = verified_client.get("/admin/search/", {"s": payload})
    assert response.status_code == 200
    assert payload.encode() not in response.content


def test_csrf_action_admin_et_login_refuses_sans_jeton(verified_client):
    guarded = Client(enforce_csrf_checks=True)
    guarded.cookies = verified_client.cookies
    n = nouvelle()
    response = guarded.post("/admin/hub/nouvelle/", {"action": "publish_selected", "_selected_action": [n.pk]})
    assert response.status_code == 403
    n.refresh_from_db()
    assert not n.publie
    assert guarded.post("/account/login/", {"login_view-current_step": "auth"}).status_code == 403


def test_csrf_origine_etrangere_refusee_meme_avec_jeton(verified_client):
    from html.parser import HTMLParser
    class Tokens(HTMLParser):
        token = None
        def handle_starttag(self, tag, attrs):
            data = dict(attrs)
            if tag == "input" and data.get("name") == "csrfmiddlewaretoken":
                self.token = data["value"]
    guarded = Client(enforce_csrf_checks=True)
    guarded.cookies = verified_client.cookies
    parser = Tokens()
    parser.feed(guarded.get("/admin/hub/nouvelle/").content.decode())
    n = nouvelle()
    response = guarded.post("/admin/hub/nouvelle/", {"csrfmiddlewaretoken": parser.token,
        "action": "publish_selected", "_selected_action": [n.pk]}, HTTP_ORIGIN="https://attacker.invalid")
    assert response.status_code == 403
    n.refresh_from_db()
    assert not n.publie


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>"])
def test_url_active_refusee_par_post_admin_sans_perte(verified_client, url):
    n = nouvelle(publie=True)
    payload = dict(titre_fr=n.titre_fr, titre_en=n.titre_en, corps_fr=n.corps_fr,
        corps_en=n.corps_en, date_jalon="2026-10-01", alt_fr="", alt_en="", _save="Enregistrer",
        **{"liens-TOTAL_FORMS": "1", "liens-INITIAL_FORMS": "0", "liens-MIN_NUM_FORMS": "0",
           "liens-MAX_NUM_FORMS": "1000", "liens-0-url": url, "liens-0-libelle_fr": "Sonde",
           "liens-0-libelle_en": "Probe", "liens-0-ordre": "0",
           "nouvellesecteur_set-TOTAL_FORMS": "0", "nouvellesecteur_set-INITIAL_FORMS": "0",
           "nouvellesecteur_set-MIN_NUM_FORMS": "0", "nouvellesecteur_set-MAX_NUM_FORMS": "1000"})
    response = verified_client.post(f"/admin/hub/nouvelle/{n.pk}/change/", payload)
    assert response.status_code == 200
    assert response.context["inline_admin_formsets"][0].formset.forms[0].errors["url"]
    assert not n.liens.exists()
    n.refresh_from_db()
    assert n.publie and n.titre_fr == "Formation réelle"


def test_staff_verifie_sans_permission_ne_peut_pas_publier(client):
    user = get_user_model().objects.create_user("staff", password="test", is_staff=True)
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client.force_login(user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    n = nouvelle()
    assert client.get("/admin/hub/nouvelle/").status_code == 403
    assert client.post("/admin/hub/nouvelle/", {"action": "publish_selected", "_selected_action": [n.pk]}).status_code == 403
    n.refresh_from_db()
    assert not n.publie


def test_image_polyglotte_reencodee_sans_html(settings, tmp_path):
    from io import BytesIO
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    settings.MEDIA_ROOT = tmp_path / "media"
    stream = BytesIO()
    Image.new("RGB", (12, 8), "blue").save(stream, "PNG")
    html = b"<script>alert('polyglot')</script>"
    n = nouvelle(image=SimpleUploadedFile("attaque.html", stream.getvalue() + html))
    assert n.image.name.endswith(".jpg")
    assert html not in n.image.read()
    with Image.open(n.image.path) as image:
        assert image.format == "JPEG"


def test_session_expiree_et_deconnexion_invalident_cookie(verified_client):
    cookie = verified_client.cookies[settings.SESSION_COOKIE_NAME].value
    Session.objects.filter(session_key=cookie).update(expire_date=timezone.now() - timedelta(seconds=1))
    assert verified_client.get("/admin/").status_code == 302


def test_logout_rejeu_cookie_refuse(verified_client):
    stolen = Client()
    stolen.cookies[settings.SESSION_COOKIE_NAME] = verified_client.cookies[settings.SESSION_COOKIE_NAME].value
    assert verified_client.post("/admin/logout/").status_code == 200
    assert stolen.get("/admin/").status_code == 302


def test_appareil_autre_compte_ne_verifie_pas_session(client, admin_user):
    other = get_user_model().objects.create_user("other", password="test")
    device = TOTPDevice.objects.create(user=other, name="default", confirmed=True)
    client.force_login(admin_user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    assert client.get("/admin/").status_code == 302


@pytest.mark.parametrize("path", ["/account/login/", "/admin/"])
def test_auth_reponses_non_stockables_et_anti_cadrage(client, path):
    response = client.get(path)
    assert "no-store" in response.headers["Cache-Control"]
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "same-origin"

