import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from tests.factories import configuration, secteur, nouvelle

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return get_user_model().objects.create_superuser("owner", "owner@example.com", "A-strong-test-password-42")


@pytest.fixture
def verified_client(client, admin_user):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    device = TOTPDevice.objects.create(user=admin_user, name="default", confirmed=True)
    client.force_login(admin_user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    return client


@pytest.mark.parametrize("path", ["/admin/", "/admin/hub/secteur/", "/admin/hub/nouvelle/add/", "/admin/search/"])
def test_admin_anonyme_et_mot_de_passe_seul_refuses(client, admin_user, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/account/login/" in response.url
    client.force_login(admin_user)
    response = client.get(path)
    assert response.status_code == 302
    assert "/account/login/" in response.url


def test_admin_non_staff_refuse_meme_otp(client):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    user = get_user_model().objects.create_user("visitor", password="test")
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client.force_login(user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    assert client.get("/admin/").status_code == 302


def test_unfold_configuration_unique_et_actions(verified_client):
    configuration()
    s = secteur()
    assert verified_client.get("/admin/").status_code == 200
    assert verified_client.get("/admin/hub/configurationgenerale/add/").status_code == 403
    response = verified_client.post("/admin/hub/secteur/", {"action": "publish_selected", "_selected_action": [s.pk]})
    assert response.status_code == 302
    s.refresh_from_db()
    assert s.publie
    verified_client.post("/admin/hub/secteur/", {"action": "unpublish_selected", "_selected_action": [s.pk]})
    s.refresh_from_db()
    assert not s.publie
    s.nom_en = ""
    s.save()
    response = verified_client.post("/admin/hub/secteur/", {"action": "publish_selected", "_selected_action": [s.pk]}, follow=True)
    assert response.status_code == 200
    s.refresh_from_db()
    assert not s.publie
    assert "nom_en" in response.content.decode()


def login_password(client, password="A-strong-test-password-42"):
    client.get("/account/login/")
    return client.post("/account/login/", {"login_view-current_step": "auth", "auth-username": "owner", "auth-password": password})


def test_connexion_reelle_totp_et_rejeu_refuse(client, admin_user):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.oath import totp
    device = TOTPDevice.objects.create(user=admin_user, name="default", confirmed=True)
    response = login_password(client)
    assert response.status_code == 200
    assert client.get("/admin/").status_code == 302
    token = str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)).zfill(device.digits)
    response = client.post("/account/login/", {"login_view-current_step": "token", "token-otp_token": token})
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 200
    client.logout()
    login_password(client)
    client.post("/account/login/", {"login_view-current_step": "token", "token-otp_token": token})
    assert client.get("/admin/").status_code == 302


def test_recuperation_code_usage_unique(client, admin_user):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
    TOTPDevice.objects.create(user=admin_user, name="default", confirmed=True)
    backup = StaticDevice.objects.create(user=admin_user, name="backup")
    StaticToken.objects.create(device=backup, token="recover42")
    login_password(client)
    client.post("/account/login/", {"wizard_goto_step": "backup", "login_view-current_step": "token"})
    response = client.post("/account/login/", {"login_view-current_step": "backup", "backup-otp_token": "recover42"})
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 200
    assert not StaticToken.objects.filter(device=backup, token="recover42").exists()
    client.logout()
    login_password(client)
    client.post("/account/login/", {"wizard_goto_step": "backup", "login_view-current_step": "token"})
    client.post("/account/login/", {"login_view-current_step": "backup", "backup-otp_token": "recover42"})
    assert client.get("/admin/").status_code == 302


def test_limitation_connexion_meme_avec_mot_de_passe_valide_apres_echecs(client, admin_user):
    for _ in range(5):
        login_password(client, password="mauvais")
    response = login_password(client)
    assert response.status_code == 429
    assert client.get("/admin/").status_code == 302


def test_enrolement_ne_donne_pas_acces_aux_contenus(client, admin_user):
    response = login_password(client)
    assert response.status_code == 302
    assert client.get("/account/two_factor/setup/").status_code == 200
    assert client.get("/admin/hub/nouvelle/").status_code == 302


def test_creation_et_modification_reelles_dans_unfold(verified_client):
    from hub.models import Nouvelle
    s = secteur()
    payload = dict(titre_fr="Formation saisie dans Unfold", titre_en="Training entered in Unfold",
                   corps_fr="Une étape réelle", corps_en="A real milestone", slug_fr="saisie", slug_en="entry",
                   date_jalon="2026-10-10", alt_fr="", alt_en="",
                   **{"liens-TOTAL_FORMS": "1", "liens-INITIAL_FORMS": "0", "liens-MIN_NUM_FORMS": "0",
                      "liens-MAX_NUM_FORMS": "1000", "liens-0-url": "https://example.com/training",
                      "liens-0-libelle_fr": "Formation", "liens-0-libelle_en": "Training", "liens-0-ordre": "0",
                      "nouvellesecteur_set-TOTAL_FORMS": "1", "nouvellesecteur_set-INITIAL_FORMS": "0",
                      "nouvellesecteur_set-MIN_NUM_FORMS": "0", "nouvellesecteur_set-MAX_NUM_FORMS": "1000",
                      "nouvellesecteur_set-0-secteur": str(s.pk), "_save": "Enregistrer"})
    response = verified_client.post("/admin/hub/nouvelle/add/", payload)
    assert response.status_code == 302
    n = Nouvelle.objects.get(slug_fr="saisie")
    assert not n.publie
    assert n.secteurs.get() == s
    assert n.liens.get().libelle_en == "Training"
    verified_client.post("/admin/hub/nouvelle/", {"action": "publish_selected", "_selected_action": [n.pk]})
    n.refresh_from_db()
    assert n.publie
    payload.update(corps_en=" ", **{"liens-INITIAL_FORMS": "1", "liens-0-id": str(n.liens.get().pk),
                   "nouvellesecteur_set-INITIAL_FORMS": "1", "nouvellesecteur_set-0-id": str(n.nouvellesecteur_set.get().pk)})
    response = verified_client.post(f"/admin/hub/nouvelle/{n.pk}/change/", payload)
    assert response.status_code == 200
    n.refresh_from_db()
    assert n.corps_en == "A real milestone"


def test_configuration_modifiee_dans_unfold_invalidite_preserve(verified_client):
    c = configuration()
    payload = {field.name: getattr(c, field.name) for field in c._meta.fields
               if field.editable and not hasattr(getattr(c, field.name), "storage")}  # fichier vide non envoyé
    payload.update(email="nouveau@example.com", presentation_en=" ", _save="Enregistrer")
    response = verified_client.post("/admin/hub/configurationgenerale/1/change/", payload)
    assert response.status_code == 200
    c.refresh_from_db()
    assert c.email == "contact@example.com"
    payload["presentation_en"] = "Project presentation"
    response = verified_client.post("/admin/hub/configurationgenerale/1/change/", payload)
    assert response.status_code == 302
    c.refresh_from_db()
    assert c.email == "nouveau@example.com"


def test_connexion_limitee_par_ip_malgre_changement_de_nom(client, admin_user):
    for index in range(5):
        client.get("/account/login/")
        client.post("/account/login/", {"login_view-current_step": "auth", "auth-username": f"inconnu-{index}", "auth-password": "mauvais"})
    response = login_password(client)
    assert response.status_code == 429


def test_codes_recuperation_inaccessibles_sans_second_facteur(client, admin_user):
    client.force_login(admin_user)
    response = client.get("/account/two_factor/backup/tokens/")
    assert response.status_code == 302
    assert client.get("/admin/login/").url.startswith("/account/login/")


def test_image_d_accueil_modifiable_dans_unfold(verified_client):
    configuration()
    html = verified_client.get("/admin/hub/configurationgenerale/1/change/").content.decode()
    assert 'name="image_accueil"' in html and 'name="alt_accueil_fr"' in html and 'name="alt_accueil_en"' in html
