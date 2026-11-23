import io
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app import app, db
from models import Note

@pytest.fixture
def client():
    orig_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    orig_upload_folder = app.config['UPLOAD_FOLDER']

    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'test_uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        # Flask-SQLAlchemy 3.x önbelleğindeki gerçek database.db motorunu yedekle ve bellek içi motor kullan
        orig_engine = db._app_engines[app].get(None)
        test_engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        db._app_engines[app][None] = test_engine

        db.create_all()
        # Test için örnek not ekle
        sample_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test_bil101.pdf')
        with open(sample_file, 'wb') as f:
            f.write(b'%PDF-1.4 test document')

        note = Note(
            title="Python Temel Notları",
            course_code="BIL101",
            course_name="Programlamaya Giriş",
            class_level=1,
            exam_type="Vize",
            file_path="test_bil101.pdf",
            file_type="pdf",
            file_size=len(b'%PDF-1.4 test document'),
            description="Örnek test notu",
            download_count=10,
            upvotes=5,
            downvotes=1,
            report_count=0,
            is_approved=True
        )
        db.session.add(note)
        db.session.commit()

        yield app.test_client()

        # Temizlik (yalnızca bellek içi test veritabanını siler)
        db.session.remove()
        db.drop_all()
        test_engine.dispose()
        if orig_engine is not None:
            db._app_engines[app][None] = orig_engine
        if os.path.exists(sample_file):
            os.remove(sample_file)
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            import shutil
            shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)

    app.config['TESTING'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = orig_db_uri
    app.config['UPLOAD_FOLDER'] = orig_upload_folder


def test_index_page(client):
    """Ana sayfanın 200 döndürdüğünü ve notu listelediğini doğrular."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"BIL101" in response.data
    assert b"Python Temel Notlar" in response.data


def test_index_filtering(client):
    """Filtrelerin doğru çalıştığını doğrular."""
    # Sınıf filtresi
    res1 = client.get('/?class_level=1')
    assert res1.status_code == 200
    assert b"BIL101" in res1.data

    res2 = client.get('/?class_level=3')
    assert res2.status_code == 200
    assert b"E\xc5\x9fle\xc5\x9fen Ders Notu Bulunamad\xc4\xb1" in res2.data  # Eşleşen not yok


def test_upload_page(client):
    """Not yükleme sayfasının 200 döndürdüğünü doğrular."""
    response = client.get('/not-yukle')
    assert response.status_code == 200
    assert b"Ders Notu & Kaynak Payla" in response.data


def test_stats_page(client):
    """İstatistikler sayfasının 200 döndürdüğünü doğrular."""
    response = client.get('/istatistikler')
    assert response.status_code == 200
    assert b"Platform & Havuz" in response.data
    assert b"BIL101" in response.data


def test_api_upload_success(client):
    """Geçerli bir dosya yükleme işlemini test eder."""
    pdf_content = b"%PDF-1.4 sample upload test data"
    data = {
        'title': 'Veri Yapıları Final Soruları',
        'course_code': 'BIL201',
        'course_name': 'Veri Yapıları',
        'class_level': '2',
        'exam_type': 'Final',
        'description': 'Ağaçlar ve bağlı listeler soruları',
        'file': (io.BytesIO(pdf_content), 'veri_yapilari.pdf')
    }

    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'note_id' in json_data


def test_api_upload_invalid_extension(client):
    """Geçersiz dosya uzantısını reddettiğini doğrular."""
    data = {
        'title': 'Tehlikeli Dosya',
        'course_code': 'BIL101',
        'course_name': 'Programlama',
        'class_level': '1',
        'exam_type': 'Vize',
        'file': (io.BytesIO(b'malicious content'), 'script.exe')
    }

    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False


def test_api_vote(client):
    """Faydalı / Yetersiz oy verme API'sini test eder."""
    # Upvote testi
    res_up = client.post('/api/vote/1', json={'vote_type': 'up'})
    assert res_up.status_code == 200
    json_up = res_up.get_json()
    assert json_up['success'] is True
    assert json_up['upvotes'] == 6

    # Downvote testi
    res_down = client.post('/api/vote/1', json={'vote_type': 'down'})
    assert res_down.status_code == 200
    json_down = res_down.get_json()
    assert json_down['success'] is True
    assert json_down['downvotes'] == 2


def test_api_report(client):
    """Hatalı not bildirim API'sini test eder."""
    response = client.post('/api/report/1', json={'reason': 'Sayfalar bulanık çıkmış'})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['report_count'] == 1


def test_download_note(client):
    """Dosya indirme ve indirme sayacının 1 arttığını test eder."""
    # Başlangıçta 10 indirme vardı
    response = client.get('/download/1')
    assert response.status_code == 200
    assert response.data == b'%PDF-1.4 test document'

    # Veritabanında indirme sayacı güncellenmiş olmalı
    with app.app_context():
        note = db.session.get(Note, 1)
        assert note.download_count == 11


def test_api_notes_json(client):
    """Anlık arama için JSON API'sini test eder."""
    response = client.get('/api/notes?q=BIL101')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['count'] == 1
    assert json_data['notes'][0]['course_code'] == 'BIL101'


def test_admin_dashboard_unauthorized(client):
    """Giriş yapılmadan admin paneline erişimin engellendiğini ve login'e yönlendirildiğini test eder."""
    response = client.get('/admin', follow_redirects=False)
    assert response.status_code == 302
    assert '/admin/login' in response.headers['Location']


def test_admin_login_and_approval_flow(client):
    """Admin girişi yapma ve bekleyen notu onaylama akışını test eder."""
    # 1. Bekleyen yeni bir not yükle (is_approved=False)
    pdf_content = b"%PDF-1.4 test pending note"
    data = {
        'title': 'Onay Bekleyen Algoritma Notu',
        'course_code': 'BIL202',
        'course_name': 'Algoritma Analizi',
        'class_level': '2',
        'exam_type': 'Vize',
        'file': (io.BytesIO(pdf_content), 'algoritma.pdf')
    }
    upload_res = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert upload_res.status_code == 201
    pending_id = upload_res.get_json()['note_id']

    # 2. Ana sayfada henüz listelenmemeli (çünkü henüz onaylanmadı)
    res_index = client.get('/')
    assert b"Onay Bekleyen Algoritma Notu" not in res_index.data

    # 3. Admin login ol
    login_res = client.post('/admin/login', data={'password': 'admin123'}, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Y\xc3\xb6netici Kontrol Paneli" in login_res.data or b"Admin Paneli" in login_res.data

    # 4. Admin panelinde onay bekleyenler arasında görünmeli
    admin_dash = client.get('/admin')
    assert b"Onay Bekleyen Algoritma Notu" in admin_dash.data

    # 5. Notu onayla
    approve_res = client.post(f'/admin/notes/{pending_id}/approve', follow_redirects=True)
    assert approve_res.status_code == 200

    # 6. Artık ana sayfada listelenmeli
    res_index_after = client.get('/')
    assert b"Onay Bekleyen Algoritma Notu" in res_index_after.data


def test_api_bologna_courses(client):
    """Bologna ders kataloğu API'sinin doğru çalıştığını test eder."""
    response = client.get('/api/courses')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['count'] >= 100
    
    # 1. sınıf filtresi
    res_lvl1 = client.get('/api/courses?class_level=1')
    assert res_lvl1.status_code == 200
    lvl1_data = res_lvl1.get_json()
    assert lvl1_data['success'] is True
    assert all(c['class_level'] == 1 for c in lvl1_data['courses'])


def test_api_upload_without_course_code(client):
    """Öğrencinin ders kodu girmeden sadece ders adıyla not yükleyebildiğini test eder."""
    pdf_content = b"%PDF-1.4 test without code"
    data = {
        'title': 'Ders Kodu Olmadan Yüklenen Not',
        'department': 'Elektrik-Elektronik Mühendisliği',
        'course_name': 'Devre Analizi-1',
        'class_level': '2',
        'exam_type': 'Vize',
        'file': (io.BytesIO(pdf_content), 'devre_notu.pdf')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['success'] is True

    # Veritabanında ders kodunun otomatik dolduğunu doğrula
    with app.app_context():
        note = db.session.get(Note, json_data['note_id'])
        assert note is not None
        assert note.course_code != "" # Otomatik belirlendi
        assert note.department == 'Elektrik-Elektronik Mühendisliği'


def test_department_filtering(client):
    """Bölüm filtresinin (Bilgisayar, Elektrik, Makine) doğru çalıştığını test eder."""
    # Bilgisayar filtresi
    res_ceng = client.get('/?department=Bilgisayar+M%C3%BChendisli%C4%9fi')
    assert res_ceng.status_code == 200

    # Makine filtresi
    res_me = client.get('/?department=Makine+M%C3%BChendisli%C4%9fi')
    assert res_me.status_code == 200


def test_admin_edit_clear_reports_and_backup(client):
    """Admin not düzenleme, şikayet nedeni görme/temizleme, oy değiştirme ve ZIP yedek indirmeyi test eder."""
    # 1. Oy değiştirme (up -> down)
    res_up = client.post('/api/vote/1', json={'vote_type': 'up'})
    assert res_up.get_json()['upvotes'] == 6
    res_switch = client.post('/api/vote/1', json={'vote_type': 'down', 'previous_vote': 'up'})
    switch_json = res_switch.get_json()
    assert switch_json['upvotes'] == 5
    assert switch_json['downvotes'] == 2

    # 2. Şikayet bildirimi ve nedeni kaydetme
    client.post('/api/report/1', json={'reason': 'Yanlış ders kodu seçilmiş'})

    # 3. Admin girişi
    client.post('/admin/login', data={'password': 'admin123'}, follow_redirects=True)
    dash = client.get('/admin')
    assert b"Yanl\xc4\xb1\xc5\x9f ders kodu se\xc3\xa7ilmi\xc5\x9f" in dash.data

    # 4. Şikayeti temizle
    clear_res = client.post('/admin/notes/1/clear-reports', follow_redirects=True)
    assert clear_res.status_code == 200
    with app.app_context():
        n = db.session.get(Note, 1)
        assert n.report_count == 0
        assert n.last_report_reason == ''

    # 5. Not bilgilerini düzenle
    edit_res = client.post('/admin/notes/1/edit', data={
        'title': 'Güncellenmiş Python Notu',
        'department': 'Bilgisayar Mühendisliği',
        'course_code': '3301256',
        'course_name': 'PROGRAMLAMA DİLİ-1',
        'class_level': '1',
        'exam_type': 'Final',
        'description': 'Admin tarafından güncellendi'
    }, follow_redirects=True)
    assert edit_res.status_code == 200
    with app.app_context():
        n = db.session.get(Note, 1)
        assert n.title == 'Güncellenmiş Python Notu'
        assert n.exam_type == 'Final'

    # 6. Admin oturumu açıkken yüklenen notun doğrudan onaylanması
    upload_res = client.post('/api/upload', data={
        'title': 'Admin Doğrudan Yükleme',
        'course_code': '3301151',
        'course_name': 'MATEMATİK-1',
        'class_level': '1',
        'exam_type': 'Vize',
        'file': (io.BytesIO(b'%PDF-1.4 admin upload'), 'admin.pdf')
    }, content_type='multipart/form-data')
    assert upload_res.status_code == 201
    new_id = upload_res.get_json()['note_id']
    with app.app_context():
        n_admin = db.session.get(Note, new_id)
        assert n_admin.is_approved is True

    # 7. Tam yedek (.zip) indirme
    backup_res = client.get('/admin/backup/download')
    assert backup_res.status_code == 200
    assert backup_res.mimetype == 'application/zip'



