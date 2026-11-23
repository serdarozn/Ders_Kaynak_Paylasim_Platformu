/**
 * SELÇUK ÜNİVERSİTESİ BİLGİSAYAR MÜHENDİSLİĞİ
 * Ders Notu ve Kaynak Dayanışma Platformu - JavaScript Modülü
 */

document.addEventListener('DOMContentLoaded', () => {
    initVoteButtons();
    initReportModal();
    initPreviewModal();
    initUploadDropzone();
    initFilterLiveSync();
});

/* ==========================================================================
   TOAST BİLDİRİM YARDIMCISI
   ========================================================================== */
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'custom-toast';

    let icon = 'fa-circle-info';
    let iconColor = '#38bdf8';
    if (type === 'success') {
        icon = 'fa-circle-check';
        iconColor = '#34d399';
    } else if (type === 'error' || type === 'danger') {
        icon = 'fa-circle-exclamation';
        iconColor = '#f87171';
    }

    toast.innerHTML = `
        <i class="fa-solid ${icon}" style="color: ${iconColor}; font-size: 1.15rem;"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3800);
}

/* ==========================================================================
   OY VERME (FAYDALI / YETERSİZ) - AJAX
   ========================================================================== */
function initVoteButtons() {
    const voteButtons = document.querySelectorAll('.btn-vote');
    
    // Daha önce oy verilmiş notları localStorage'dan al
    const votedNotes = JSON.parse(localStorage.getItem('suk_voted_notes') || '{}');

    // Sayfa yüklendiğinde aktif oyları işaretle
    voteButtons.forEach(btn => {
        const noteId = btn.dataset.noteId;
        const voteType = btn.dataset.voteType;
        if (votedNotes[noteId] === voteType) {
            btn.classList.add(voteType === 'up' ? 'voted-up' : 'voted-down');
        }
    });

    voteButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const noteId = btn.dataset.noteId;
            const voteType = btn.dataset.voteType;

            // Zaten aynı oyu vermişse uyar
            if (votedNotes[noteId] === voteType) {
                showToast('Bu not için zaten oyunuzu kullandınız.', 'info');
                return;
            }

            const previousVote = votedNotes[noteId] || null;
            btn.disabled = true;

            try {
                const response = await fetch(`/api/vote/${noteId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ vote_type: voteType, previous_vote: previousVote })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    // Sayacı güncelle
                    const card = btn.closest('.note-card');
                    if (card) {
                        const upSpan = card.querySelector(`.btn-vote[data-vote-type="up"] .vote-count`);
                        const downSpan = card.querySelector(`.btn-vote[data-vote-type="down"] .vote-count`);
                        if (upSpan) upSpan.textContent = result.upvotes;
                        if (downSpan) downSpan.textContent = result.downvotes;

                        // Buton stillerini güncelle
                        card.querySelectorAll('.btn-vote').forEach(b => {
                            b.classList.remove('voted-up', 'voted-down');
                        });
                        btn.classList.add(voteType === 'up' ? 'voted-up' : 'voted-down');
                    }

                    // LocalStorage kaydet
                    votedNotes[noteId] = voteType;
                    localStorage.setItem('suk_voted_notes', JSON.stringify(votedNotes));

                    showToast(
                        voteType === 'up' 
                            ? 'Faydalı oyu kaydedildi! Dayanışmaya katkınız için teşekkürler.' 
                            : 'Geri bildiriminiz kaydedildi.', 
                        'success'
                    );
                } else {
                    showToast(result.message || 'Oy kaydedilemedi.', 'error');
                }
            } catch (err) {
                console.error('Vote error:', err);
                showToast('Bir bağlantı hatası oluştu.', 'error');
            } finally {
                btn.disabled = false;
            }
        });
    });
}

/* ==========================================================================
   HATALI İÇERİK BİLDİRİMİ (REPORT MODAL)
   ========================================================================== */
let activeReportNoteId = null;

function initReportModal() {
    const reportButtons = document.querySelectorAll('.btn-report');
    const modalEl = document.getElementById('reportModal');
    const submitBtn = document.getElementById('btnSubmitReport');
    const noteTitleSpan = document.getElementById('reportNoteTitle');
    const reasonSelect = document.getElementById('reportReason');
    const otherDetails = document.getElementById('reportOtherDetails');

    if (!modalEl || !submitBtn) return;

    const bsModal = new bootstrap.Modal(modalEl);

    reportButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            activeReportNoteId = btn.dataset.noteId;
            const title = btn.dataset.noteTitle || 'Bu Not';
            if (noteTitleSpan) noteTitleSpan.textContent = title;
            if (otherDetails) otherDetails.value = '';
            bsModal.show();
        });
    });

    submitBtn.addEventListener('click', async () => {
        if (!activeReportNoteId) return;

        const reason = reasonSelect ? reasonSelect.value : 'Belirtilmedi';
        const details = otherDetails ? otherDetails.value.trim() : '';
        const fullReason = details ? `${reason} - Açıklama: ${details}` : reason;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>İletiliyor...';

        try {
            const response = await fetch(`/api/report/${activeReportNoteId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ reason: fullReason })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                bsModal.hide();
                showToast(result.message, 'success');
            } else {
                showToast(result.message || 'Bildirim iletilemedi.', 'error');
            }
        } catch (err) {
            console.error('Report error:', err);
            showToast('Bağlantı hatası oluştu.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i> Bildirimi Gönder';
        }
    });
}

/* ==========================================================================
   BELGE ÖNİZLEME MODALI (PREVIEW MODAL)
   ========================================================================== */
function initPreviewModal() {
    const previewButtons = document.querySelectorAll('.btn-preview');
    const modalEl = document.getElementById('previewModal');
    const titleEl = document.getElementById('previewModalTitle');
    const downloadDirectLink = document.getElementById('previewModalDownloadBtn');
    const bodyEl = document.getElementById('previewModalContent');

    if (!modalEl || !bodyEl) return;

    const bsModal = new bootstrap.Modal(modalEl);

    previewButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const noteId = btn.dataset.noteId;
            const title = btn.dataset.noteTitle || 'Belge Önizleme';
            const fileType = (btn.dataset.fileType || '').toLowerCase();
            const previewUrl = `/preview/${noteId}`;
            const downloadUrl = `/download/${noteId}`;

            if (titleEl) titleEl.textContent = title;
            if (downloadDirectLink) downloadDirectLink.href = downloadUrl;

            // İçeriği oluştur (PDF ise iframe/embed, Resim ise img)
            if (fileType === 'pdf') {
                bodyEl.innerHTML = `
                    <iframe src="${previewUrl}#toolbar=0" class="preview-iframe" title="PDF Önizleme"></iframe>
                `;
            } else {
                bodyEl.innerHTML = `
                    <div class="p-3 text-center w-100">
                        <img src="${previewUrl}" class="preview-img rounded" alt="${title}" />
                    </div>
                `;
            }

            bsModal.show();
        });
    });

    // Modal kapandığında iframe belleğini temizle
    modalEl.addEventListener('hidden.bs.modal', () => {
        bodyEl.innerHTML = '';
    });
}

/* ==========================================================================
   SÜRÜKLE-BIRAK (DRAG & DROP) DOSYA YÜKLEME
   ========================================================================== */
function initUploadDropzone() {
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('noteFileInput');
    const filePreview = document.getElementById('filePreview');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const fileSizeDisplay = document.getElementById('fileSizeDisplay');
    const removeFileBtn = document.getElementById('btnRemoveFile');
    const uploadForm = document.getElementById('noteUploadForm');
    const courseCodeInput = document.getElementById('course_code');
    const courseNameInput = document.getElementById('course_name');

    if (!dropzone || !fileInput) return;

    // Selçuk Bilgisayar Mühendisliği Bologna ve Genel Müfredat Ders Kataloğu
    const courseDirectory = {
        "BIL101": {
                "name": "Programlamaya Giriş",
                "level": 1
        },
        "BIL103": {
                "name": "Bilgisayar Mühendisliğine Giriş",
                "level": 1
        },
        "BIL105": {
                "name": "Matematik I",
                "level": 1
        },
        "BIL107": {
                "name": "Fizik I",
                "level": 1
        },
        "BIL102": {
                "name": "Nesne Yönelimli Programlama",
                "level": 1
        },
        "BIL104": {
                "name": "Matematik II",
                "level": 1
        },
        "BIL106": {
                "name": "Fizik II",
                "level": 1
        },
        "BIL201": {
                "name": "Veri Yapıları",
                "level": 2
        },
        "BIL203": {
                "name": "Sayısal Mantık Tasarımı",
                "level": 2
        },
        "BIL205": {
                "name": "Diferansiyel Denklemler",
                "level": 2
        },
        "BIL202": {
                "name": "Algoritma Analizi",
                "level": 2
        },
        "BIL204": {
                "name": "Elektrik ve Elektronik Devreler",
                "level": 2
        },
        "BIL301": {
                "name": "İşletim Sistemleri",
                "level": 3
        },
        "BIL303": {
                "name": "Veritabanı Sistemleri",
                "level": 3
        },
        "BIL305": {
                "name": "Bilgisayar Mimarisi",
                "level": 3
        },
        "BIL302": {
                "name": "Bilgisayar Ağları",
                "level": 3
        },
        "BIL304": {
                "name": "Yazılım Mühendisliği",
                "level": 3
        },
        "BIL306": {
                "name": "Web Teknolojileri",
                "level": 3
        },
        "BIL401": {
                "name": "Makine Öğrenmesi",
                "level": 4
        },
        "BIL403": {
                "name": "Derleyici Tasarımı",
                "level": 4
        },
        "BIL405": {
                "name": "Dağıtık Sistemler",
                "level": 4
        },
        "BIL407": {
                "name": "Yapay Zeka",
                "level": 4
        },
        "BIL402": {
                "name": "Bilgi Güvenliği ve Kriptoloji",
                "level": 4
        },
        "3301151": {
                "name": "MATEMATİK-1",
                "level": 1
        },
        "3311151": {
                "name": "MATEMATİK-1 (İ.Ö.)",
                "level": 1
        },
        "3301152": {
                "name": "FİZİK-1",
                "level": 1
        },
        "3311152": {
                "name": "FİZİK-1 (İ.Ö.)",
                "level": 1
        },
        "3301153": {
                "name": "TÜRK DİLİ I",
                "level": 1
        },
        "3311153": {
                "name": "TÜRK DİLİ I (İ.Ö.)",
                "level": 1
        },
        "3301154": {
                "name": "ATATÜRK İLKELERİ VE İNKILAP TARİHİ-1",
                "level": 1
        },
        "3311154": {
                "name": "ATATÜRK İLKELERİ VE İNKILAP TARİHİ-1 (İ.Ö.)",
                "level": 1
        },
        "3301155": {
                "name": "YABANCI DİL-1",
                "level": 1
        },
        "3311155": {
                "name": "YABANCI DİL-1 (İ.Ö.)",
                "level": 1
        },
        "3301156": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİNE GİRİŞ",
                "level": 1
        },
        "3311156": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİNE GİRİŞ (İ.Ö.)",
                "level": 1
        },
        "3301157": {
                "name": "İŞ SAĞLIĞI VE GÜVENLİĞİ-1",
                "level": 1
        },
        "3311157": {
                "name": "İŞ SAĞLIĞI VE GÜVENLİĞİ-1 (İ.Ö.)",
                "level": 1
        },
        "3301158": {
                "name": "LİNEER CEBİR",
                "level": 1
        },
        "3311158": {
                "name": "LİNEER CEBİR (İ.Ö.)",
                "level": 1
        },
        "3301251": {
                "name": "MATEMATİK-2",
                "level": 1
        },
        "3311251": {
                "name": "MATEMATİK-2 (İ.Ö.)",
                "level": 1
        },
        "3301252": {
                "name": "FİZİK-2",
                "level": 1
        },
        "3311252": {
                "name": "FİZİK-2 (İ.Ö.)",
                "level": 1
        },
        "3301253": {
                "name": "TÜRK DİLİ II",
                "level": 1
        },
        "3311253": {
                "name": "TÜRK DİLİ II (İ.Ö.)",
                "level": 1
        },
        "3301254": {
                "name": "ATATÜRK İLKELERİ VE İNKILAP TARİHİ-2",
                "level": 1
        },
        "3311254": {
                "name": "ATATÜRK İLKELERİ VE İNKILAP TARİHİ-2 (İ.Ö.)",
                "level": 1
        },
        "3301255": {
                "name": "YABANCI DİL-2",
                "level": 1
        },
        "3311255": {
                "name": "YABANCI DİL-2 (İ.Ö.)",
                "level": 1
        },
        "3301256": {
                "name": "PROGRAMLAMA DİLİ-1",
                "level": 1
        },
        "3311256": {
                "name": "PROGRAMLAMA DİLİ-1 (İ.Ö.)",
                "level": 1
        },
        "3301257": {
                "name": "İŞ SAĞLIĞI VE GÜVENLİĞİ-2",
                "level": 1
        },
        "3311257": {
                "name": "İŞ SAĞLIĞI VE GÜVENLİĞİ-2 (İ.Ö.)",
                "level": 1
        },
        "3301258": {
                "name": "AYRIK MATEMATİK",
                "level": 1
        },
        "3311258": {
                "name": "AYRIK MATEMATİK (İ.Ö.)",
                "level": 1
        },
        "3301351": {
                "name": "NESNEYE YÖNELİK PROGRAMLAMA DİLİ",
                "level": 2
        },
        "3311351": {
                "name": "NESNEYE YÖNELİK PROGRAMLAMA DİLİ (İ.Ö.)",
                "level": 2
        },
        "3301352": {
                "name": "İŞLETİM SİSTEMLERİ",
                "level": 2
        },
        "3311352": {
                "name": "İŞLETİM SİSTEMLERİ (İ.Ö.)",
                "level": 2
        },
        "3301353": {
                "name": "MANTIK DEVRELERİ-1",
                "level": 2
        },
        "3311353": {
                "name": "MANTIK DEVRELERİ-1 (İ.Ö.)",
                "level": 2
        },
        "3301354": {
                "name": "VERİ YAPILARI VE UYGULAMALARI",
                "level": 2
        },
        "3311354": {
                "name": "VERİ YAPILARI VE UYGULAMALARI (İ.Ö.)",
                "level": 2
        },
        "3301355": {
                "name": "ELEKTRONİK DEVRE ELEMANLARI VE ÖLÇME",
                "level": 2
        },
        "3311355": {
                "name": "ELEKTRONİK DEVRE ELEMANLARI VE ÖLÇME (İ.Ö.)",
                "level": 2
        },
        "3301356": {
                "name": "SAYISAL YÖNTEMLER",
                "level": 2
        },
        "3311356": {
                "name": "SAYISAL YÖNTEMLER (İ.Ö.)",
                "level": 2
        },
        "3301357": {
                "name": "iSTATİSTİK VE OLASILIK",
                "level": 2
        },
        "3311357": {
                "name": "iSTATİSTİK VE OLASILIK (İ.Ö.)",
                "level": 2
        },
        "3301451": {
                "name": "MÜHENDİSLİK MATEMATİĞİ",
                "level": 2
        },
        "3311451": {
                "name": "MÜHENDİSLİK MATEMATİĞİ (İ.Ö.)",
                "level": 2
        },
        "3301452": {
                "name": "PROGRAMLAMA DİLİ-2",
                "level": 2
        },
        "3311452": {
                "name": "PROGRAMLAMA DİLİ-2 (İ.Ö.)",
                "level": 2
        },
        "3301453": {
                "name": "MANTIK DEVRELERİ-2",
                "level": 2
        },
        "3311453": {
                "name": "MANTIK DEVRELERİ-2 (İ.Ö.)",
                "level": 2
        },
        "3301454": {
                "name": "VERİTABANI YÖNETİM SİSTEMLERİ",
                "level": 2
        },
        "3311454": {
                "name": "VERİTABANI YÖNETİM SİSTEMLERİ (İ.Ö.)",
                "level": 2
        },
        "3301455": {
                "name": "YAZILIM MÜHENDİSLİĞİ",
                "level": 2
        },
        "3311455": {
                "name": "YAZILIM MÜHENDİSLİĞİ (İ.Ö.)",
                "level": 2
        },
        "3301456": {
                "name": "MOBİL PROGRAMLAMA",
                "level": 2
        },
        "3311456": {
                "name": "MOBİL PROGRAMLAMA (İ.Ö.)",
                "level": 2
        },
        "3301461": {
                "name": "TEKNOLOJİ TARİHİ",
                "level": 2
        },
        "3311461": {
                "name": "TEKNOLOJİ TARİHİ (İ.Ö.)",
                "level": 2
        },
        "3301462": {
                "name": "İŞ HUKUKU VE ETİK",
                "level": 2
        },
        "3311462": {
                "name": "İŞ HUKUKU VE ETİK (İ.Ö.)",
                "level": 2
        },
        "3301463": {
                "name": "İLETİŞİM BECERİLERİ VE AKADEMİK RAPORLAMA",
                "level": 2
        },
        "3311463": {
                "name": "İLETİŞİM BECERİLERİ VE AKADEMİK RAPORLAMA (İ.Ö.)",
                "level": 2
        },
        "3301464": {
                "name": "SOSYAL SORUMLULUK VE DEĞERLER EĞİTİMİ",
                "level": 2
        },
        "3311464": {
                "name": "SOSYAL SORUMLULUK VE DEĞERLER EĞİTİMİ (İ.Ö.)",
                "level": 2
        },
        "3301465": {
                "name": "ETKİLİ İLETİŞİM VE BEDEN DİLİ",
                "level": 2
        },
        "3311465": {
                "name": "ETKİLİ İLETİŞİM VE BEDEN DİLİ (İ.Ö.)",
                "level": 2
        },
        "3301466": {
                "name": "MEDYA OKUR YAZARLIĞI",
                "level": 2
        },
        "3311466": {
                "name": "MEDYA OKUR YAZARLIĞI (İ.Ö.)",
                "level": 2
        },
        "3301467": {
                "name": "YÖNETİM VE ORGANİZASYON",
                "level": 2
        },
        "3311467": {
                "name": "YÖNETİM VE ORGANİZASYON (İ.Ö.)",
                "level": 2
        },
        "3301468": {
                "name": "ÇEVRE VE EKOLOJİ",
                "level": 2
        },
        "3311468": {
                "name": "ÇEVRE VE EKOLOJİ (İ.Ö.)",
                "level": 2
        },
        "3301469": {
                "name": "YAŞAM BOYU ÖĞRENME",
                "level": 2
        },
        "3311469": {
                "name": "YAŞAM BOYU ÖĞRENME (İ.Ö.)",
                "level": 2
        },
        "3301470": {
                "name": "İLETİŞİM VE STRES YÖNETİMİ",
                "level": 2
        },
        "3311470": {
                "name": "İLETİŞİM VE STRES YÖNETİMİ (İ.Ö.)",
                "level": 2
        },
        "3301471": {
                "name": "GÖNÜLLÜLÜK ÇALIŞMALARI",
                "level": 2
        },
        "3311471": {
                "name": "GÖNÜLLÜLÜK ÇALIŞMALARI (İ.Ö.)",
                "level": 2
        },
        "3301472": {
                "name": "DİJİTAL DÖNÜŞÜM",
                "level": 2
        },
        "3311472": {
                "name": "DİJİTAL DÖNÜŞÜM (İ.Ö.)",
                "level": 2
        },
        "3301473": {
                "name": "SOSYAL İNGİLİZCE",
                "level": 2
        },
        "3311473": {
                "name": "SOSYAL İNGİLİZCE (İ.Ö.)",
                "level": 2
        },
        "3301551": {
                "name": "MİKROİŞLEMCİLER VE MİKRODENETLEYİCİLER",
                "level": 3
        },
        "3311551": {
                "name": "MİKROİŞLEMCİLER VE MİKRODENETLEYİCİLER (İ.Ö.)",
                "level": 3
        },
        "3301552": {
                "name": "PROGRAMLAMA DİLİ-3",
                "level": 3
        },
        "3311552": {
                "name": "PROGRAMLAMA DİLİ-3 (İ.Ö.)",
                "level": 3
        },
        "3301553": {
                "name": "VERİ HABERLEŞMESİ VE AĞLAR",
                "level": 3
        },
        "3311553": {
                "name": "VERİ HABERLEŞMESİ VE AĞLAR (İ.Ö.)",
                "level": 3
        },
        "3301554": {
                "name": "TEKNİK İNGİLİZCE",
                "level": 3
        },
        "3311554": {
                "name": "TEKNİK İNGİLİZCE (İ.Ö.)",
                "level": 3
        },
        "3301561": {
                "name": "SİNYAL İŞLEME",
                "level": 3
        },
        "3311561": {
                "name": "SİNYAL İŞLEME (İ.Ö.)",
                "level": 3
        },
        "3301562": {
                "name": "TASARIM DESENLERİ",
                "level": 3
        },
        "3311562": {
                "name": "TASARIM DESENLERİ (İ.Ö.)",
                "level": 3
        },
        "3301563": {
                "name": "İNSAN BİLGİSAYAR ETKİLEŞİMİ",
                "level": 3
        },
        "3311563": {
                "name": "İNSAN BİLGİSAYAR ETKİLEŞİMİ (İ.Ö.)",
                "level": 3
        },
        "3301564": {
                "name": "BİYOMEDİKAL SİSTEMLER",
                "level": 3
        },
        "3311564": {
                "name": "BİYOMEDİKAL SİSTEMLER (İ.Ö.)",
                "level": 3
        },
        "3301565": {
                "name": "SİMÜLASYON VE MODELLEME",
                "level": 3
        },
        "3311565": {
                "name": "SİMÜLASYON VE MODELLEME (İ.Ö.)",
                "level": 3
        },
        "3301566": {
                "name": "BİLGİSAYAR DONANIMI",
                "level": 3
        },
        "3311566": {
                "name": "BİLGİSAYAR DONANIMI (İ.Ö.)",
                "level": 3
        },
        "3301567": {
                "name": "WEB TASARIMI",
                "level": 3
        },
        "3311567": {
                "name": "WEB TASARIMI (İ.Ö.)",
                "level": 3
        },
        "3301568": {
                "name": "VERİ MADENCİLİĞİ",
                "level": 3
        },
        "3311568": {
                "name": "VERİ MADENCİLİĞİ (İ.Ö.)",
                "level": 3
        },
        "3301569": {
                "name": "ADLİ BİLİŞİM",
                "level": 3
        },
        "3311569": {
                "name": "ADLİ BİLİŞİM (İ.Ö.)",
                "level": 3
        },
        "3301570": {
                "name": "VERİ TABANI PROGRMALAMA",
                "level": 3
        },
        "3311570": {
                "name": "VERİ TABANI PROGRMALAMA (İ.Ö.)",
                "level": 3
        },
        "3301571": {
                "name": "MAKİNE ÖĞRENMESİ",
                "level": 3
        },
        "3311571": {
                "name": "MAKİNE ÖĞRENMESİ (İ.Ö.)",
                "level": 3
        },
        "3301572": {
                "name": "ALGORİTMA ANALİZİ",
                "level": 3
        },
        "3311572": {
                "name": "ALGORİTMA ANALİZİ (İ.Ö.)",
                "level": 3
        },
        "3301573": {
                "name": "DOĞAL DİL İŞLEME TEMELLERİ",
                "level": 3
        },
        "3311573": {
                "name": "DOĞAL DİL İŞLEME TEMELLERİ (İ.Ö.)",
                "level": 3
        },
        "3301574": {
                "name": "NESNELERİN İNTERNETİ",
                "level": 3
        },
        "3311574": {
                "name": "NESNELERİN İNTERNETİ (İ.Ö.)",
                "level": 3
        },
        "3301575": {
                "name": "İLERİ DİJİTAL SİSTEMLER",
                "level": 3
        },
        "3311575": {
                "name": "İLERİ DİJİTAL SİSTEMLER (İ.Ö.)",
                "level": 3
        },
        "3301576": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİNDE ÖZEL KONULAR",
                "level": 3
        },
        "3311576": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİNDE ÖZEL KONULAR (İ.Ö.)",
                "level": 3
        },
        "3301577": {
                "name": "SİBER SİSTEMLER VE BİLGİ GÜVENLİĞİ",
                "level": 3
        },
        "3311577": {
                "name": "SİBER SİSTEMLER VE BİLGİ GÜVENLİĞİ (İ.Ö.)",
                "level": 3
        },
        "3301578": {
                "name": "SÜRDÜRÜLEBİLİR YAZILIM MÜHENDİSLİĞİ",
                "level": 3
        },
        "3311578": {
                "name": "SÜRDÜRÜLEBİLİR YAZILIM MÜHENDİSLİĞİ (İ.Ö.)",
                "level": 3
        },
        "3301651": {
                "name": "YAPAY ZEKA",
                "level": 3
        },
        "3311651": {
                "name": "YAPAY ZEKA (İ.Ö.)",
                "level": 3
        },
        "3301652": {
                "name": "OTOMATA TEORİSİ VE BİÇİMSEL DİLLER",
                "level": 3
        },
        "3311652": {
                "name": "OTOMATA TEORİSİ VE BİÇİMSEL DİLLER (İ.Ö.)",
                "level": 3
        },
        "3301653": {
                "name": "GÖRÜNTÜ İŞLEME",
                "level": 3
        },
        "3311653": {
                "name": "GÖRÜNTÜ İŞLEME (İ.Ö.)",
                "level": 3
        },
        "3301654": {
                "name": "MÜHENDİSLİK TASARIMI",
                "level": 3
        },
        "3311654": {
                "name": "MÜHENDİSLİK TASARIMI (İ.Ö.)",
                "level": 3
        },
        "3301661": {
                "name": "SİSTEM PROGRAMLAMA",
                "level": 3
        },
        "3311661": {
                "name": "SİSTEM PROGRAMLAMA (İ.Ö.)",
                "level": 3
        },
        "3301662": {
                "name": "BİLGİSAYAR VE AĞ GÜVENLİĞİ",
                "level": 3
        },
        "3311662": {
                "name": "BİLGİSAYAR VE AĞ GÜVENLİĞİ (İ.Ö.)",
                "level": 3
        },
        "3301663": {
                "name": "GÖMÜLÜ SİSTEMLER",
                "level": 3
        },
        "3311663": {
                "name": "GÖMÜLÜ SİSTEMLER (İ.Ö.)",
                "level": 3
        },
        "3301664": {
                "name": "İŞ ZEKASI",
                "level": 3
        },
        "3311664": {
                "name": "İŞ ZEKASI (İ.Ö.)",
                "level": 3
        },
        "3301665": {
                "name": "ROBOTİK",
                "level": 3
        },
        "3311665": {
                "name": "ROBOTİK (İ.Ö.)",
                "level": 3
        },
        "3301666": {
                "name": "İŞLETİM SİSTEMLERİ YÖNETİMİ",
                "level": 3
        },
        "3311666": {
                "name": "İŞLETİM SİSTEMLERİ YÖNETİMİ (İ.Ö.)",
                "level": 3
        },
        "3301667": {
                "name": "WEB SERVİSLERİ",
                "level": 3
        },
        "3311667": {
                "name": "WEB SERVİSLERİ (İ.Ö.)",
                "level": 3
        },
        "3301668": {
                "name": "MİKROBİLGİSAYARLI SİSTEM TASARIMI",
                "level": 3
        },
        "3311668": {
                "name": "MİKROBİLGİSAYARLI SİSTEM TASARIMI (İ.Ö.)",
                "level": 3
        },
        "3301669": {
                "name": "MESLEKİ İNGİLİZCE",
                "level": 3
        },
        "3311669": {
                "name": "MESLEKİ İNGİLİZCE (İ.Ö.)",
                "level": 3
        },
        "3301670": {
                "name": "KRİPTOLOJİ",
                "level": 3
        },
        "3311670": {
                "name": "KRİPTOLOJİ (İ.Ö.)",
                "level": 3
        },
        "3301671": {
                "name": "BİLGİSAYAR BİLİMLERİNDE İNOVASYON VE ARAŞTIRMA TEKNİKLERİ",
                "level": 3
        },
        "3311671": {
                "name": "BİLGİSAYAR BİLİMLERİNDE İNOVASYON VE ARAŞTIRMA TEKNİKLERİ (İ.Ö.)",
                "level": 3
        },
        "3301672": {
                "name": "DİSİPLİNLERARASI ÇALIŞMA",
                "level": 3
        },
        "3311672": {
                "name": "DİSİPLİNLERARASI ÇALIŞMA (İ.Ö.)",
                "level": 3
        },
        "3301673": {
                "name": "GERÇEKÇİ MODELLEME VE SİMÜLASYON TASARIMI",
                "level": 3
        },
        "3311673": {
                "name": "GERÇEKÇİ MODELLEME VE SİMÜLASYON TASARIMI (İ.Ö.)",
                "level": 3
        },
        "3301674": {
                "name": "WEB PROGRAMLAMA",
                "level": 3
        },
        "3311674": {
                "name": "WEB PROGRAMLAMA (İ.Ö.)",
                "level": 3
        },
        "3301675": {
                "name": "SÜRDÜRÜLEBİLİR BİLİŞİM TEKNOLOJİLERİ",
                "level": 3
        },
        "3311675": {
                "name": "SÜRDÜRÜLEBİLİR BİLİŞİM TEKNOLOJİLERİ (İ.Ö.)",
                "level": 3
        },
        "3301676": {
                "name": "STEGANOGRAFİ",
                "level": 3
        },
        "3311676": {
                "name": "STEGANOGRAFİ (İ.Ö.)",
                "level": 3
        },
        "3301751": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİ UYGULAMALARI",
                "level": 4
        },
        "3311751": {
                "name": "BİLGİSAYAR MÜHENDİSLİĞİ UYGULAMALARI (İ.Ö.)",
                "level": 4
        },
        "3301752": {
                "name": "BİLGİSAYAR MİMARİSİ VE ORGANİZASYONU",
                "level": 4
        },
        "3311752": {
                "name": "BİLGİSAYAR MİMARİSİ VE ORGANİZASYONU (İ.Ö.)",
                "level": 4
        },
        "3301753": {
                "name": "VERİ BİLİMİ",
                "level": 4
        },
        "3311753": {
                "name": "VERİ BİLİMİ (İ.Ö.)",
                "level": 4
        },
        "3301754": {
                "name": "GİRİŞİMCİLİK VE PROJE YÖNETİMİ",
                "level": 4
        },
        "3311754": {
                "name": "GİRİŞİMCİLİK VE PROJE YÖNETİMİ (İ.Ö.)",
                "level": 4
        },
        "3301761": {
                "name": "PROG. MANTIK KONTROLLÖR",
                "level": 4
        },
        "3311761": {
                "name": "PROG. MANTIK KONTROLLÖR (İ.Ö.)",
                "level": 4
        },
        "3301762": {
                "name": "PARALEL İŞLEMCİLİ SİSTEMLER",
                "level": 4
        },
        "3311762": {
                "name": "PARALEL İŞLEMCİLİ SİSTEMLER (İ.Ö.)",
                "level": 4
        },
        "3301763": {
                "name": "KONTROL SİSTEMLERİ",
                "level": 4
        },
        "3311763": {
                "name": "KONTROL SİSTEMLERİ (İ.Ö.)",
                "level": 4
        },
        "3301764": {
                "name": "BİLGİSAYAR DESTEKLİ TASARIM",
                "level": 4
        },
        "3311764": {
                "name": "BİLGİSAYAR DESTEKLİ TASARIM (İ.Ö.)",
                "level": 4
        },
        "3301765": {
                "name": "YÖNEYLEM ARAŞTIRMASI",
                "level": 4
        },
        "3311765": {
                "name": "YÖNEYLEM ARAŞTIRMASI (İ.Ö.)",
                "level": 4
        },
        "3301766": {
                "name": "KABLOSUZ AĞLAR",
                "level": 4
        },
        "3311766": {
                "name": "KABLOSUZ AĞLAR (İ.Ö.)",
                "level": 4
        },
        "3301767": {
                "name": "BULUT BİLİŞİM",
                "level": 4
        },
        "3311767": {
                "name": "BULUT BİLİŞİM (İ.Ö.)",
                "level": 4
        },
        "3301768": {
                "name": "PAKET PROGRAMLAR",
                "level": 4
        },
        "3311768": {
                "name": "PAKET PROGRAMLAR (İ.Ö.)",
                "level": 4
        },
        "3301769": {
                "name": "BİLGİSAYAR GRAFİKLERİ",
                "level": 4
        },
        "3311769": {
                "name": "BİLGİSAYAR GRAFİKLERİ (İ.Ö.)",
                "level": 4
        },
        "3301770": {
                "name": "VERİ İLETİŞİM TEKNİKLERİ",
                "level": 4
        },
        "3311770": {
                "name": "VERİ İLETİŞİM TEKNİKLERİ (İ.Ö.)",
                "level": 4
        },
        "3301771": {
                "name": "OYUN PROGRAMLAMA",
                "level": 4
        },
        "3311771": {
                "name": "OYUN PROGRAMLAMA (İ.Ö.)",
                "level": 4
        },
        "3301772": {
                "name": "E-TİCARET VE UYGULAMALARI",
                "level": 4
        },
        "3311772": {
                "name": "E-TİCARET VE UYGULAMALARI (İ.Ö.)",
                "level": 4
        },
        "3301773": {
                "name": "PARALEL PROGRAMLAMA",
                "level": 4
        },
        "3311773": {
                "name": "PARALEL PROGRAMLAMA (İ.Ö.)",
                "level": 4
        },
        "3301774": {
                "name": "MVC TABANLI WEB MİMARİSİ",
                "level": 4
        },
        "3311774": {
                "name": "MVC TABANLI WEB MİMARİSİ (İ.Ö.)",
                "level": 4
        },
        "3301775": {
                "name": "YEŞİL BİLİŞİM",
                "level": 4
        },
        "3311775": {
                "name": "YEŞİL BİLİŞİM (İ.Ö.)",
                "level": 4
        },
        "3301776": {
                "name": "ÇEVRE VE ENERJİ",
                "level": 4
        },
        "3311776": {
                "name": "ÇEVRE VE ENERJİ (İ.Ö.)",
                "level": 4
        },
        "3301777": {
                "name": "BLOKZİNCİR TEMELLERİ",
                "level": 4
        },
        "3311777": {
                "name": "BLOKZİNCİR TEMELLERİ (İ.Ö.)",
                "level": 4
        },
        "3301778": {
                "name": "BÜYÜK VERİ ANALİTİĞİ",
                "level": 4
        },
        "3311778": {
                "name": "BÜYÜK VERİ ANALİTİĞİ (İ.Ö.)",
                "level": 4
        },
        "3301779": {
                "name": "BİLGİSAYARLA GÖRME",
                "level": 4
        },
        "3311779": {
                "name": "BİLGİSAYARLA GÖRME (İ.Ö.)",
                "level": 4
        },
        "3301782": {
                "name": "KALİTE VE GÜVENCE SİSTEMLERİ",
                "level": 4
        },
        "3311782": {
                "name": "KALİTE VE GÜVENCE SİSTEMLERİ (İ.Ö.)",
                "level": 4
        },
        "3301783": {
                "name": "MÜHENDİSLİK EKONOMİSİ",
                "level": 4
        },
        "3311783": {
                "name": "MÜHENDİSLİK EKONOMİSİ (İ.Ö.)",
                "level": 4
        },
        "3301784": {
                "name": "İŞARET DİLİ",
                "level": 4
        },
        "3311784": {
                "name": "İŞARET DİLİ (İ.Ö.)",
                "level": 4
        },
        "3301785": {
                "name": "DIŞ TİCARET",
                "level": 4
        },
        "3311785": {
                "name": "DIŞ TİCARET (İ.Ö.)",
                "level": 4
        },
        "3301786": {
                "name": "TOPLUMA HİZMET UYGULAMALARI",
                "level": 4
        },
        "3311786": {
                "name": "TOPLUMA HİZMET UYGULAMALARI (İ.Ö.)",
                "level": 4
        },
        "3301787": {
                "name": "REKLAMCILIK VE STRATEJİLERİ",
                "level": 4
        },
        "3311787": {
                "name": "REKLAMCILIK VE STRATEJİLERİ (İ.Ö.)",
                "level": 4
        },
        "3301788": {
                "name": "ARAŞTIRMA VE RAPOR YAZMA TEKNİKLERİ",
                "level": 4
        },
        "3311788": {
                "name": "ARAŞTIRMA VE RAPOR YAZMA TEKNİKLERİ (İ.Ö.)",
                "level": 4
        },
        "3301789": {
                "name": "MÜHENDİSLİK ETİĞİ",
                "level": 4
        },
        "3311789": {
                "name": "MÜHENDİSLİK ETİĞİ (İ.Ö.)",
                "level": 4
        },
        "3301851": {
                "name": "İŞLETMEDE MESLEKİ EĞİTİM",
                "level": 4
        },
        "3311851": {
                "name": "İŞLETMEDE MESLEKİ EĞİTİM (İ.Ö.)",
                "level": 4
        },
        "3301852": {
                "name": "STAJ-1",
                "level": 4
        },
        "3311852": {
                "name": "STAJ-1 (İ.Ö.)",
                "level": 4
        },
        "3301853": {
                "name": "STAJ-2",
                "level": 4
        },
        "3311853": {
                "name": "STAJ-2 (İ.Ö.)",
                "level": 4
        }
};

    const classLevelSelect = document.getElementById('class_level');

    if (courseCodeInput && courseNameInput) {
        courseCodeInput.addEventListener('input', () => {
            const val = courseCodeInput.value.trim().toUpperCase();
            if (courseDirectory[val]) {
                const courseInfo = courseDirectory[val];
                const cName = typeof courseInfo === 'string' ? courseInfo : courseInfo.name;
                const cLevel = typeof courseInfo === 'object' ? courseInfo.level : null;

                if (!courseNameInput.value || courseNameInput.value === '') {
                    courseNameInput.value = cName;
                }
                if (cLevel && classLevelSelect && (!classLevelSelect.value || classLevelSelect.value === '')) {
                    classLevelSelect.value = cLevel;
                }
            }
        });
    }

    // Tıklayınca dosya seçiciyi aç
    dropzone.addEventListener('click', (e) => {
        if (e.target !== removeFileBtn && !removeFileBtn?.contains(e.target)) {
            fileInput.click();
        }
    });

    // Drag-over ve Drop olayları
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleSelectedFile(fileInput.files[0]);
        }
    });

    function handleSelectedFile(file) {
        const validExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!validExtensions.includes(ext)) {
            showToast('Sadece PDF, JPG, JPEG veya PNG dosyaları kabul edilir!', 'error');
            fileInput.value = '';
            return;
        }

        const maxSize = 25 * 1024 * 1024; // 25 MB
        if (file.size > maxSize) {
            showToast('Dosya boyutu 25 MB sınırını aşıyor!', 'error');
            fileInput.value = '';
            return;
        }

        // Seçilen dosyayı DataTransfer ile input'a ata
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;

        if (fileNameDisplay) fileNameDisplay.textContent = file.name;
        if (fileSizeDisplay) {
            const mbSize = (file.size / (1024 * 1024)).toFixed(2);
            fileSizeDisplay.textContent = `${mbSize} MB`;
        }

        if (filePreview) filePreview.style.display = 'flex';
        dropzone.querySelector('.dropzone-prompt')?.classList.add('d-none');
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            if (filePreview) filePreview.style.display = 'none';
            dropzone.querySelector('.dropzone-prompt')?.classList.remove('d-none');
        });
    }

    // Form gönderimini ele al (AJAX ile güzel geri bildirim)
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Lütfen yüklenecek bir not dosyası seçiniz.', 'error');
                return;
            }

            const submitBtn = document.getElementById('btnSubmitUpload');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Yükleniyor ve Doğrulanıyor...';
            }

            const formData = new FormData(uploadForm);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1200);
                } else {
                    showToast(result.message || 'Yükleme sırasında bir hata oluştu.', 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnHtml;
                    }
                }
            } catch (err) {
                console.error('Upload error:', err);
                showToast('Yükleme sırasında sunucu veya ağ hatası oluştu.', 'error');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                }
            }
        });
    }
}

/* ==========================================================================
   FİLTRE DEĞİŞİKLİĞİNDE OTOMATİK FORM GÖNDERİMİ
   ========================================================================== */
function initFilterLiveSync() {
    const filterForm = document.getElementById('filterForm');
    if (!filterForm) return;

    const autoSubmits = filterForm.querySelectorAll('select');
    autoSubmits.forEach(select => {
        select.addEventListener('change', () => {
            filterForm.submit();
        });
    });
}
