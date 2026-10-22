import sqlite3
from contextlib import closing
from uuid import UUID

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from tests.factories import configuration
from tests.factories import nouvelle, secteur
from tests.test_admin import admin_user, verified_client

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def private_storage(settings, tmp_path):
    settings.DATABASE_BACKUP_DIR = tmp_path / 'private'
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


def test_page_protegee_et_accessible(client, admin_user, verified_client):
    client.logout()
    assert client.get('/admin/database/').status_code == 302
    client.force_login(admin_user)
    assert client.get('/admin/database/').status_code == 302


def test_sauvegarde_permutation_et_email(verified_client, settings, admin_user):
    c = configuration()
    response = verified_client.get('/admin/database/')
    assert response.status_code == 200
    assert 'Base courante' in response.content.decode()
    response = verified_client.post('/admin/database/', {'action': 'save'})
    assert response.status_code == 302
    backup = settings.DATABASE_BACKUP_DIR / 'backup.sqlite3'
    with closing(sqlite3.connect(backup)) as db:
        assert db.execute('SELECT email FROM hub_configurationgenerale').fetchone()[0] == 'contact@example.com'
        ident, created = db.execute('SELECT uuid, created_at FROM hub_databaseversion').fetchone()
        assert UUID(ident)
        assert created
    c.email = 'updated@example.com'
    c.save()
    response = verified_client.post('/admin/database/', {'action': 'swap', 'confirm': 'on'})
    assert response.status_code == 302
    c.refresh_from_db()
    assert c.email == 'contact@example.com'
    # Security identity stays current, even after activating older content.
    assert admin_user.__class__.objects.get(pk=admin_user.pk).email == 'owner@example.com'
    # Reconnect after activation invalidates sessions.
    from django_otp.plugins.otp_totp.models import TOTPDevice
    verified_client.force_login(admin_user)
    session = verified_client.session
    session['otp_device_id'] = TOTPDevice.objects.get(user=admin_user).persistent_id
    session.save()
    response = verified_client.post('/admin/database/', {'action': 'email', 'email': 'other@example.com'})
    assert response.status_code == 302
    assert mail.outbox[0].to == ['other@example.com']
    filename, data, mime = mail.outbox[0].attachments[0]
    assert filename.startswith('ventisax-') and 'UTC' in filename
    assert data.startswith(b'SQLite format 3')
    assert list(settings.DATABASE_BACKUP_DIR.glob('*.sqlite3')) == [backup]
    with closing(sqlite3.connect(backup)) as db:
        assert db.execute('SELECT email FROM hub_configurationgenerale').fetchone()[0] == 'updated@example.com'


def test_import_invalide_et_confirmation_preservent_donnees(verified_client):
    c = configuration()
    response = verified_client.post('/admin/database/', {
        'action': 'upload_current', 'confirm': 'on',
        'database': SimpleUploadedFile('bad.sqlite3', b'not a database'),
    })
    assert response.status_code == 200
    c.refresh_from_db()
    assert c.email == 'contact@example.com'
    assert verified_client.post('/admin/database/', {'action': 'swap'}).status_code == 200


def test_email_admin_par_defaut_et_destinataire_invalide(verified_client):
    assert verified_client.post('/admin/database/', {'action': 'email', 'email': 'bad'}).status_code == 200
    assert not mail.outbox
    assert verified_client.post('/admin/database/', {'action': 'email'}).status_code == 302
    assert mail.outbox[0].to == ['owner@example.com']


def exported(verified_client):
    verified_client.post('/admin/database/', {'action': 'email'})
    return mail.outbox[-1].attachments[0][1]


def reconnect(client, user):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    client.force_login(user)
    session = client.session
    session['otp_device_id'] = TOTPDevice.objects.get(user=user).persistent_id
    session.save()


def test_charger_deux_slots_preserve_acces_et_revoque_sessions(verified_client, admin_user, settings):
    from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
    from django.contrib.sessions.models import Session
    c = configuration()
    s = secteur(publie=True)
    n = nouvelle(publie=True)
    n.secteurs.add(s)
    recovery = StaticDevice.objects.create(user=admin_user, name='backup')
    StaticToken.objects.create(device=recovery, token='old-code')
    data = exported(verified_client)
    StaticToken.objects.all().delete()
    admin_user.email = 'new-owner@example.com'
    admin_user.save()
    c.email = 'live@example.com'
    c.save()
    response = verified_client.post('/admin/database/', {'action': 'upload_backup', 'confirm': 'on', 'database': SimpleUploadedFile('db.sqlite3', data)})
    assert response.status_code == 302
    c.refresh_from_db()
    assert c.email == 'live@example.com'
    for action, expected_email in (('upload_current', 'contact@example.com'), ('swap', 'live@example.com'), ('swap', 'contact@example.com')):
        payload = {'action': action, 'confirm': 'on'}
        if action == 'upload_current':
            payload['database'] = SimpleUploadedFile('db.sqlite3', data)
        response = verified_client.post('/admin/database/', payload)
        assert response.status_code == 302
        assert not Session.objects.exists()
        assert not StaticToken.objects.exists()
        admin_user.refresh_from_db()
        assert admin_user.email == 'new-owner@example.com'
        c.refresh_from_db()
        assert c.email == expected_email
        assert n.__class__.objects.get(pk=n.pk).uuid == n.uuid
        assert verified_client.get('/fr/nouvelles/formation/').status_code == 200
        reconnect(verified_client, admin_user)
    assert len(list(settings.DATABASE_BACKUP_DIR.glob('*.sqlite3'))) == 1


@pytest.mark.parametrize('mutation', [
    'DROP TABLE hub_liennouvelle',
    "DELETE FROM django_migrations WHERE app='hub'",
    "UPDATE hub_nouvelle SET date_jalon=NULL WHERE publie=1",
    "UPDATE hub_secteur SET site_url='javascript:alert(1)'",
    "UPDATE hub_configurationgenerale SET academie_url='javascript:alert(1)'",
    "UPDATE hub_configurationgenerale SET tiktok_url='https://evil.example/'",
    "UPDATE hub_nouvelle SET facebook_url='https://evil.example/' WHERE publie=1",
    "UPDATE hub_nouvelle SET video_youtube='https://www.youtube.com/playlist?list=PL0123456789' WHERE publie=1",
    "UPDATE hub_nouvelle SET compte_rendu_fr='Objet : essai', compte_rendu_en='' WHERE publie=1",
    "UPDATE hub_nouvelle SET uuid='invalid'",
])
def test_import_incompatible_preserve_slots(verified_client, settings, mutation):
    configuration()
    secteur(publie=True)
    nouvelle(publie=True)
    data = exported(verified_client)
    with closing(sqlite3.connect(':memory:')) as db:
        db.deserialize(data)
        db.execute(mutation)
        db.commit()
        bad = db.serialize()
    response = verified_client.post('/admin/database/', {'action': 'upload_backup', 'confirm': 'on', 'database': SimpleUploadedFile('bad.sqlite3', bad)})
    assert response.status_code == 200
    assert not (settings.DATABASE_BACKUP_DIR / 'backup.sqlite3').exists()


def test_echec_stockage_ne_change_pas_courante(verified_client, monkeypatch):
    c = configuration()
    data = exported(verified_client)
    c.email = 'live@example.com'
    c.save()
    def disk_full(db):
        raise OSError('disk full')
    monkeypatch.setattr('hub.database_versions.store_backup', disk_full)
    response = verified_client.post('/admin/database/', {'action': 'upload_current', 'confirm': 'on', 'database': SimpleUploadedFile('db.sqlite3', data)})
    assert response.status_code == 200
    c.refresh_from_db()
    assert c.email == 'live@example.com'


def test_csrf_et_staff_sans_superuser_refuses(verified_client, admin_user):
    from django.test import Client
    strict = Client(enforce_csrf_checks=True)
    strict.cookies = verified_client.cookies
    assert strict.post('/admin/database/', {'action': 'save'}).status_code == 403
    admin_user.is_superuser = False
    admin_user.save()
    assert verified_client.get('/admin/database/').status_code == 403


def test_limites_et_smtp_echec_sans_faux_succes(verified_client, settings, monkeypatch):
    settings.DATABASE_MAX_BYTES = 8
    assert verified_client.post('/admin/database/', {'action': 'upload_backup', 'confirm': 'on', 'database': SimpleUploadedFile('db.sqlite3', b'123456789')}).status_code == 200
    settings.DATABASE_MAX_BYTES = 20 * 1024 * 1024
    settings.DATABASE_EMAIL_MAX_BYTES = 1
    assert verified_client.post('/admin/database/', {'action': 'email'}).status_code == 200
    assert not mail.outbox
    settings.DATABASE_EMAIL_MAX_BYTES = 10 * 1024 * 1024
    import smtplib
    def refused(message):
        raise smtplib.SMTPException('unavailable')
    monkeypatch.setattr('django.core.mail.EmailMessage.send', refused)
    assert verified_client.post('/admin/database/', {'action': 'email'}).status_code == 200
    assert not mail.outbox


def test_telecharger_slots_sans_creer_troisieme_base(verified_client, settings):
    configuration()
    response = verified_client.get('/admin/database/?download=current')
    assert response.status_code == 200
    assert response.content.startswith(b'SQLite format 3')
    assert 'UTC' in response['Content-Disposition']
    verified_client.post('/admin/database/', {'action': 'save'})
    response = verified_client.get('/admin/database/?download=backup')
    assert response.content.startswith(b'SQLite format 3')
    assert len(list(settings.DATABASE_BACKUP_DIR.glob('*.sqlite3'))) == 1


def test_image_du_backup_conservee_puis_restaurable(verified_client, settings, tmp_path):
    from io import BytesIO
    from PIL import Image
    from pathlib import Path
    settings.MEDIA_ROOT = tmp_path / 'media'
    configuration()
    stream = BytesIO()
    Image.new('RGB', (24, 16), 'red').save(stream, 'PNG')
    n = nouvelle(image=SimpleUploadedFile('image.png', stream.getvalue()), alt_fr='Preuve', alt_en='Proof', publie=True)
    name = n.image.path
    verified_client.post('/admin/database/', {'action': 'save'})
    n.image = ''
    n.save()
    assert Path(name).exists()
    assert verified_client.post('/admin/database/', {'action': 'swap', 'confirm': 'on'}).status_code == 302
    n.refresh_from_db()
    assert n.image.path == name
    assert Path(name).exists()


def test_remplacement_backup_nettoie_image_devenue_inutile(verified_client, settings, tmp_path):
    from io import BytesIO
    from PIL import Image
    from pathlib import Path
    settings.MEDIA_ROOT = tmp_path / 'media'
    stream = BytesIO()
    Image.new('RGB', (20, 20), 'blue').save(stream, 'PNG')
    n = nouvelle(image=SimpleUploadedFile('old.png', stream.getvalue()))
    name = Path(n.image.path)
    verified_client.post('/admin/database/', {'action': 'save'})
    n.image = ''
    n.save()
    assert name.exists()
    assert verified_client.post('/admin/database/', {'action': 'save', 'confirm': 'on'}).status_code == 302
    assert not name.exists()


def test_utc_stocke_et_affichage_douala(verified_client):
    from datetime import datetime, timezone
    from hub.models import DatabaseVersion
    DatabaseVersion.objects.create(pk=1, created_at=datetime(2026, 10, 10, 12, 30, tzinfo=timezone.utc))
    response = verified_client.get('/admin/database/')
    assert '13:30:00' in response.content.decode()
    assert '2026-10-10T12:30:00+00:00' in response.content.decode()
    verified_client.post('/admin/database/', {'action': 'email'})
    with closing(sqlite3.connect(':memory:')) as db:
        db.deserialize(mail.outbox[-1].attachments[0][1])
        assert db.execute('SELECT created_at FROM hub_databaseversion').fetchone()[0] == '2026-10-10 12:30:00'


def test_migration_uuid_preserve_contenus_existants(tmp_path):
    import os
    import subprocess
    import sys
    code = f'''
import os
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
from django.conf import settings
settings.DATABASES['default']['NAME']={str(tmp_path / 'migration.sqlite3')!r}
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
executor=MigrationExecutor(connection)
old=[('hub','0006_alter_configurationgenerale_whatsapp')]
executor.migrate(old)
apps=executor.loader.project_state(old).apps
sector=apps.get_model('hub','Secteur')
sector.objects.create(nom_fr='A', slug_fr='a')
sector.objects.create(nom_fr='B', slug_fr='b')
executor=MigrationExecutor(connection)
executor.migrate(executor.loader.graph.leaf_nodes())
from hub.models import Secteur
rows=list(Secteur.objects.order_by('pk').values_list('nom_fr','slug_fr','uuid'))
assert [(r[0],r[1]) for r in rows]==[('A','a'),('B','b')]
assert rows[0][2] != rows[1][2]
connection.close()
'''
    result = subprocess.run([sys.executable, '-c', code], env=os.environ.copy(), capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr


def test_migration_academie_preserve_configuration_existante(tmp_path):
    import os
    import subprocess
    import sys
    code = f'''
import os
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
from django.conf import settings
settings.DATABASES['default']['NAME']={str(tmp_path / 'academie.sqlite3')!r}
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
executor=MigrationExecutor(connection)
old=[('hub','0011_nouvelle_compte_rendu')]
executor.migrate(old)
apps=executor.loader.project_state(old).apps
apps.get_model('hub','ConfigurationGenerale').objects.create(pk=1, email='porteur@example.com', whatsapp='+237699123456', identite_fr='Ventisax')
executor=MigrationExecutor(connection)
executor.migrate([('hub','0012_configurationgenerale_academie_url')])
from hub.models import ConfigurationGenerale
c=ConfigurationGenerale.objects.get()
assert (c.email, c.whatsapp, c.identite_fr, c.academie_url) == ('porteur@example.com', '+237699123456', 'Ventisax', '')
connection.close()
'''
    result = subprocess.run([sys.executable, '-c', code], env=os.environ.copy(), capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr


def test_upload_trop_grand_refuse_avant_stockage(verified_client, settings):
    settings.DATABASE_MAX_BYTES = 8
    response = verified_client.post('/admin/database/', {'action': 'upload_backup', 'database': SimpleUploadedFile('large.sqlite3', b'x' * 100000)})
    assert response.status_code == 413
    assert not (settings.DATABASE_BACKUP_DIR / 'backup.sqlite3').exists()
