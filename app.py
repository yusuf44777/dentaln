import streamlit as st
import random
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

st.set_page_config(
    page_title="Dentaln",
    page_icon="🦷",
    layout="wide"
)

def get_secret(key, default=""):
    """Önce st.secrets, sonra os.getenv'den oku. Hem lokal hem cloud çalışır."""
    try:
        val = st.secrets.get(key, None)
        if val is not None:
            return val
    except Exception:
        pass
    return os.getenv(key, default)

IZINLI_EMAILLER = [
    e.strip() for e in get_secret("IZINLI_EMAILLER", "").split(",") if e.strip()
]

if 'giris_yapildi' not in st.session_state:
    st.session_state.giris_yapildi = False
if 'kullanici_email' not in st.session_state:
    st.session_state.kullanici_email = ""

if not st.session_state.giris_yapildi:
    st.title("🔐 Dentaln - Giriş")
    st.markdown("### Devam etmek için lütfen e-posta adresinizi girin")
    email_input = st.text_input("E-posta Adresiniz:", placeholder="ornek@email.com")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 Giriş Yap", type="primary"):
            if email_input.lower() in [e.lower() for e in IZINLI_EMAILLER]:
                st.session_state.giris_yapildi = True
                st.session_state.kullanici_email = email_input
                st.rerun()
            else:
                st.error("❌ Bu e-posta adresi yetkili değil.")
    st.divider()
    st.info("💡 Erişim için kayıtlı e-posta adresinizi kullanmanız gerekmektedir.")
    st.stop()

st.title("🦷 Dentaln: Diş Hekimleri için LinkedIn Asistanı")
st.markdown(f"""
**Communitive Dentistry Üsküdar** 2026 Açılış Etkinliği için özel olarak hazırlanmıştır.  
LinkedIn profilinin **tüm bölümlerini** saniyeler içinde profesyonelce oluşturur.

*Hoş geldin, {st.session_state.kullanici_email}!* 👋
""")

if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_yapildi = False
    st.session_state.kullanici_email = ""
    st.rerun()

st.divider()


def cv_regex_parser(text):
    """CV metninden regex ve keyword ile tüm bilgileri çeker."""
    data = {}

    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 3 and not any(kw in line.lower() for kw in ["cv", "özgeçmiş", "resume", "curriculum", "vitae", "sayfa", "page"]):
            data["ad_soyad"] = line
            break

    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    data["email"] = emails[0] if emails else ""

    telefonlar = re.findall(r'(?:\+90|0)?\s*[\(]?\d{3}[\)]?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}', text)
    data["telefon"] = telefonlar[0].strip() if telefonlar else ""

    urls = re.findall(r'https?://[\w./\-@#?&=]+', text)
    linkedin_urls = [u for u in urls if 'linkedin' in u.lower()]
    other_urls = [u for u in urls if 'linkedin' not in u.lower()]
    data["website"] = other_urls[0] if other_urls else ""
    data["linkedin"] = linkedin_urls[0] if linkedin_urls else ""

    univ_db = {
        "üsküdar": "Üsküdar Üniversitesi", "istanbul": "İstanbul Üniversitesi",
        "hacettepe": "Hacettepe Üniversitesi", "ankara": "Ankara Üniversitesi",
        "marmara": "Marmara Üniversitesi", "ege": "Ege Üniversitesi",
        "gazi": "Gazi Üniversitesi", "süleyman demirel": "Süleyman Demirel Üniversitesi",
        "selçuk": "Selçuk Üniversitesi", "atatürk": "Atatürk Üniversitesi",
        "erciyes": "Erciyes Üniversitesi", "dokuz eylül": "Dokuz Eylül Üniversitesi",
        "yeditepe": "Yeditepe Üniversitesi", "başkent": "Başkent Üniversitesi",
        "medipol": "Medipol Üniversitesi", "altınbaş": "Altınbaş Üniversitesi",
        "biruni": "Biruni Üniversitesi", "bezmiâlem": "Bezmiâlem Vakıf Üniversitesi",
    }
    data["universite"] = ""
    text_lower = text.lower()
    for key, val in univ_db.items():
        if key in text_lower:
            data["universite"] = val
            break
    if not data["universite"]:
        univ_match = re.search(r'([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)\s*[Üü]niversitesi', text)
        if univ_match:
            data["universite"] = univ_match.group(0).strip()

    fakulte_keywords = ["Diş Hekimliği", "Dental", "Dentistry", "Dişhekimliği"]
    data["fakulte"] = "Diş Hekimliği Fakültesi"
    for fk in fakulte_keywords:
        if fk.lower() in text_lower:
            data["fakulte"] = "Diş Hekimliği Fakültesi"
            break

    gpa_match = re.search(r'(?:GPA|GANO|not ortalaması|genel\s*not)[:\s]*([0-3]\.[0-9]{1,2})\s*/\s*4', text, re.IGNORECASE)
    if not gpa_match:
        gpa_match = re.search(r'([0-3]\.[0-9]{1,2})\s*/\s*4\.0{0,2}', text)
    data["gpa"] = gpa_match.group(0).strip() if gpa_match else ""

    sehirler = ["İstanbul", "Ankara", "İzmir", "Antalya", "Bursa", "Eskişehir",
                "Konya", "Trabzon", "Kayseri", "Gaziantep", "Diyarbakır", "Samsun"]
    data["konum"] = ""
    for s in sehirler:
        if s.lower() in text_lower:
            data["konum"] = f"{s}, Türkiye"
            break

    dil_patterns = {
        "Türkçe": r'[Tt]ürk[çc]e[^\n]*', "İngilizce": r'[İiIı]ngilizce[^\n]*',
        "Almanca": r'[Aa]lmanca[^\n]*', "Fransızca": r'[Ff]rans[ıi]zca[^\n]*',
        "İspanyolca": r'[İiIı]spanyolca[^\n]*', "Arapça": r'[Aa]rap[çc]a[^\n]*',
        "Rusça": r'[Rr]us[çc]a[^\n]*', "English": r'English[^\n]*',
        "German": r'German[^\n]*', "French": r'French[^\n]*',
    }
    bulunan_diller = []
    for dil_adi, pattern in dil_patterns.items():
        match = re.search(pattern, text)
        if match:
            satir = match.group(0).strip()
            seviye = ""
            for s_kw in ["Ana Dil", "Native", "C2", "C1", "B2", "B1", "A2", "A1",
                         "Advanced", "Upper Intermediate", "Intermediate", "Pre-Intermediate",
                         "Elementary", "Beginner", "İleri", "Orta", "Başlangıç", "Fluent"]:
                if s_kw.lower() in satir.lower():
                    seviye = s_kw
                    break
            bulunan_diller.append(f"{dil_adi} - {seviye}" if seviye else dil_adi)
    data["diller"] = "\n".join(bulunan_diller)

    sertifika_keywords = ["sertifika", "certificate", "certification", "kurs", "course",
                          "eğitim programı", "workshop", "seminer", "BLS", "CPR",
                          "ilk yardım", "first aid", "radyasyon", "udemy", "coursera",
                          "linkedin learning"]
    sertifika_satirlari = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if line_clean and any(kw.lower() in line_clean.lower() for kw in sertifika_keywords):
            if len(line_clean) > 5 and len(line_clean) < 200:
                sertifika_satirlari.append(line_clean.lstrip("•-– "))
    data["sertifikalar"] = "\n".join(list(dict.fromkeys(sertifika_satirlari))[:10])

    topluluk_keywords = ["topluluk", "kulüp", "club", "dernek", "association",
                         "society", "öğrenci kolu", "TDB", "IADS", "IFMSA",
                         "communitive", "komite", "konsey"]
    topluluk_satirlari = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if line_clean and any(kw.lower() in line_clean.lower() for kw in topluluk_keywords):
            if len(line_clean) > 3 and len(line_clean) < 200:
                topluluk_satirlari.append(line_clean.lstrip("•-– "))
    data["topluluklar"] = "\n".join(list(dict.fromkeys(topluluk_satirlari))[:10])

    gonulluluk_keywords = ["gönüllü", "volunteer", "toplum hizmeti", "sosyal sorumluluk",
                           "farkındalık", "tarama", "kampanya", "bağış", "yardım"]
    gonulluluk_satirlari = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if line_clean and any(kw.lower() in line_clean.lower() for kw in gonulluluk_keywords):
            if len(line_clean) > 5 and len(line_clean) < 200:
                gonulluluk_satirlari.append(line_clean.lstrip("•-– "))
    data["gonulluluk"] = "\n".join(list(dict.fromkeys(gonulluluk_satirlari))[:10])

    proje_keywords = ["proje", "project", "araştırma", "research", "yayın", "publication",
                      "poster", "tez", "thesis", "makale", "article", "vaka", "case study",
                      "TÜBİTAK", "literatür", "derleme"]
    proje_satirlari = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if line_clean and any(kw.lower() in line_clean.lower() for kw in proje_keywords):
            if len(line_clean) > 5 and len(line_clean) < 200:
                proje_satirlari.append(line_clean.lstrip("•-– "))
    data["projeler"] = "\n".join(list(dict.fromkeys(proje_satirlari))[:10])

    basari_keywords = ["ödül", "award", "başarı", "burs", "scholarship", "dean's list",
                       "onur", "honor", "derece", "birincilik", "ikincilik", "üçüncülük",
                       "TÜBİTAK", "YKS", "LGS", "şampiy", "finalist"]
    basari_satirlari = []
    for line in text.split("\n"):
        line_clean = line.strip()
        if line_clean and any(kw.lower() in line_clean.lower() for kw in basari_keywords):
            if len(line_clean) > 3 and len(line_clean) < 200:
                basari_satirlari.append(line_clean.lstrip("•-– "))
    data["basarilar"] = "\n".join(list(dict.fromkeys(basari_satirlari))[:10])

    return data


def cv_ai_parser(text, key):
    """GPT ile CV'den yapılandırılmış veri çeker."""
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen bir CV analiz uzmanısın. Verilen CV metninden bilgileri çıkar ve JSON formatında döndür. "
                        "Sadece JSON döndür, başka hiçbir şey yazma. Bulamadığın alanları boş string bırak."
                    )
                },
                {
                    "role": "user",
                    "content": f"""Bu CV metninden aşağıdaki bilgileri çıkar ve JSON olarak döndür:

{text[:4000]}

JSON formatı:
{{
  "ad_soyad": "",
  "email": "",
  "telefon": "",
  "website": "",
  "konum": "",
  "universite": "",
  "fakulte": "",
  "gpa": "",
  "diller": "her dil ayrı satırda, seviye ile birlikte",
  "sertifikalar": "her sertifika ayrı satırda",
  "topluluklar": "her topluluk ayrı satırda",
  "gonulluluk": "her gönüllü deneyim ayrı satırda",
  "projeler": "her proje ayrı satırda",
  "basarilar": "her başarı/ödül ayrı satırda",
  "klinik_ilgi": "tespit ettiğin klinik ilgi alanları virgülle ayrılmış",
  "diger_ilgi": "tespit ettiğin klinik dışı yetkinlikler virgülle ayrılmış"
}}"""
                }
            ],
            max_completion_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            return json.loads(json_match.group(0))
        return {}
    except Exception as e:
        st.sidebar.warning(f"AI CV analizi başarısız: {str(e)[:80]}")
        return {}



st.sidebar.header("📋 Profil Bilgilerin")

cv_secim = st.sidebar.radio("Nasıl Bilgi Girmek İstersin?", ["Manuel Giriş", "CV Yükle"])
cv_text = ""
cv_data = {}  # Parsed CV verisi

if cv_secim == "CV Yükle":
    st.sidebar.info("💡 CV'ni yükle, bilgiler **otomatik çıkarılacak**!")
    cv_dosya = st.sidebar.file_uploader("CV'ni Yükle (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    if cv_dosya is not None:
        st.sidebar.success(f"✅ {cv_dosya.name} yüklendi!")
        if cv_dosya.type == "application/pdf":
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(cv_dosya)
                for page in pdf_reader.pages:
                    cv_text += page.extract_text()
            except:
                st.sidebar.error("PDF okuma hatası.")
        elif cv_dosya.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                import docx
                doc = docx.Document(cv_dosya)
                cv_text = "\n".join([para.text for para in doc.paragraphs])
            except:
                st.sidebar.error("DOCX okuma hatası.")
        else:
            cv_text = cv_dosya.read().decode("utf-8")

        if cv_text:
            cv_data = cv_regex_parser(cv_text)

            env_api_key_cv = get_secret("OPENAI_API_KEY", "").strip()
            if env_api_key_cv:
                with st.sidebar.status("🤖 AI ile CV analiz ediliyor...", expanded=False):
                    ai_data = cv_ai_parser(cv_text, env_api_key_cv)
                    if ai_data:
                        for key_name, val in ai_data.items():
                            if val and isinstance(val, str) and val.strip():
                                cv_data[key_name] = val.strip()
                        st.sidebar.success("🤖 AI analizi tamamlandı!")

            st.sidebar.divider()
            st.sidebar.caption("✏️ Aşağıdaki alanlar CV'nden otomatik dolduruldu. Kontrol edip düzeltebilirsin.")
    else:
        st.sidebar.warning("👆 CV dosyanı yükle — tüm alanlar otomatik dolacak!")

def cv_get(field, default=""):
    return cv_data.get(field, "").strip() or default


st.sidebar.subheader("👤 Kişisel Bilgiler")
ad_soyad = st.sidebar.text_input("Adın Soyadın", cv_get("ad_soyad", "" if cv_secim == "CV Yükle" else "Örn: Mahir Yusuf Açan"))
konum = st.sidebar.text_input("Konum (Şehir)", cv_get("konum", "İstanbul, Türkiye"))
email_goster = st.sidebar.text_input("LinkedIn'de gösterilecek e-posta", cv_get("email"), placeholder="ornek@email.com")
telefon = st.sidebar.text_input("Telefon (opsiyonel)", cv_get("telefon"), placeholder="+90 5XX XXX XX XX")
website = st.sidebar.text_input("Kişisel Website / Portfolio (opsiyonel)", cv_get("website"), placeholder="https://...")

st.sidebar.subheader("🎓 Eğitim Bilgileri")
universite = st.sidebar.text_input("Üniversiten", cv_get("universite", "Üsküdar Üniversitesi"))
fakulte = st.sidebar.text_input("Fakülte", cv_get("fakulte", "Diş Hekimliği Fakültesi"))
sinif = st.sidebar.selectbox("Kaçıncı Sınıfsın?",
    ["1. Sınıf", "2. Sınıf", "3. Sınıf", "4. Sınıf", "5. Sınıf (Stajyer Dth.)", "Yeni Mezun"]
)
baslangic_yili = st.sidebar.selectbox("Eğitim Başlangıç Yılı", list(range(2026, 2018, -1)), index=3)
bitis_yili = st.sidebar.selectbox("Beklenen Mezuniyet Yılı", list(range(2030, 2024, -1)), index=2)
gpa = st.sidebar.text_input("GPA / Not Ortalaması", cv_get("gpa"), placeholder="3.45 / 4.00")

st.sidebar.subheader("🔬 Uzmanlık & İlgi Alanları")

klinik_secenekler = ["Estetik Diş Hekimliği", "Oral Cerrah", "Ortodonti", "Endodonti", "Pedodonti",
     "Periodontoloji", "İmplantoloji", "Protetik Diş Hekimliği", "Radyoloji",
     "Ağız Patolojisi", "Restoratif Diş Hekimliği"]
cv_klinik_raw = cv_get("klinik_ilgi", "")
cv_klinik_default = []
if cv_klinik_raw:
    for secenek in klinik_secenekler:
        if secenek.lower() in cv_klinik_raw.lower():
            cv_klinik_default.append(secenek)

diger_secenekler = ["Yapay Zeka", "Veri Analizi", "Dental Fotoğrafçılık", "Sosyal Medya Yönetimi",
     "Liderlik", "Akademik Araştırma", "3D Baskı / CAD-CAM", "Halk Sağlığı",
     "Girişimcilik", "Eğitim / Mentorluk"]
cv_diger_raw = cv_get("diger_ilgi", "")
cv_diger_default = []
if cv_diger_raw:
    for secenek in diger_secenekler:
        if secenek.lower() in cv_diger_raw.lower():
            cv_diger_default.append(secenek)

klinik_ilgi = st.sidebar.multiselect(
    "Klinik İlgi Alanların",
    klinik_secenekler,
    default=cv_klinik_default if cv_klinik_default else ["Estetik Diş Hekimliği"]
)

diger_ilgi = st.sidebar.multiselect(
    "Klinik Dışı Yetkinliklerin",
    diger_secenekler,
    default=cv_diger_default if cv_diger_default else ["Akademik Araştırma"]
)

st.sidebar.subheader("🏛️ Topluluklar & Aktiviteler")
topluluklar = st.sidebar.text_area(
    "Üye Olduğun Topluluklar / Kulüpler (her satıra bir tane)",
    value=cv_get("topluluklar"),
    placeholder="Communitive Dentistry Üsküdar\nTDB Öğrenci Kolu"
)

st.sidebar.subheader("📜 Sertifikalar & Kurslar")
sertifikalar = st.sidebar.text_area(
    "Sertifikalar / kurslar (her satıra bir tane)",
    value=cv_get("sertifikalar"),
    placeholder="Temel Yaşam Desteği (BLS) Sertifikası\nCAD/CAM Dijital Diş Hekimliği Kursu"
)

st.sidebar.subheader("🤝 Gönüllü Deneyimler")
gonulluluk = st.sidebar.text_area(
    "Gönüllü çalışmaların (her satıra bir tane)",
    value=cv_get("gonulluluk"),
    placeholder="Toplum Ağız Sağlığı Taraması\nDiş Fırçalama Eğitimi - İlkokul Projesi"
)

st.sidebar.subheader("🔬 Projeler & Araştırmalar")
projeler = st.sidebar.text_area(
    "Projeler, araştırmalar, yayınlar (her satıra bir tane)",
    value=cv_get("projeler"),
    placeholder="Yapay Zeka ile Çürük Tespiti\nDijital Gülüş Tasarımı Vaka Çalışması"
)

st.sidebar.subheader("🗣️ Dil Bilgisi")
diller = st.sidebar.text_area(
    "Bildiğin diller ve seviyeleri (her satıra bir tane)",
    value=cv_get("diller"),
    placeholder="Türkçe - Ana Dil\nİngilizce - B2\nAlmanca - A2"
)

st.sidebar.subheader("🏆 Başarılar & Ödüller")
basarilar = st.sidebar.text_area(
    "Başarılar, ödüller, burslar (her satıra bir tane)",
    value=cv_get("basarilar"),
    placeholder="YKS ilk 5000\nDean's List 2024\nTÜBİTAK Proje Desteği"
)

st.sidebar.subheader("🎯 LinkedIn Hedefin")
hedef = st.sidebar.radio(
    "Şu anki LinkedIn Hedefin Ne?",
    ["Staj Bulmak", "Network Genişletmek", "Yurt Dışı Olanakları", "Sadece Vitrin Oluşturmak"]
)

st.sidebar.divider()
st.sidebar.header("⚙️ Oluşturma Ayarları")

dil_secim = st.sidebar.radio(
    "🌐 Çıktı Dili",
    ["🇹🇷 Türkçe", "🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"],
    index=0
)

generator_modu = st.sidebar.radio(
    "🧠 Oluşturma Yöntemi",
    ["📝 Şablon (Hızlı)", "🤖 AI ile Oluştur (GPT-5.2)"],
    index=0
)

api_key = None
if generator_modu == "🤖 AI ile Oluştur (GPT-5.2)":
    st.sidebar.divider()
    st.sidebar.subheader("🔑 OpenAI API Anahtarı")
    env_api_key = get_secret("OPENAI_API_KEY", "").strip()
    if env_api_key:
        st.sidebar.success("✅ API anahtarı yüklendi.")
        api_key = env_api_key
        if st.sidebar.checkbox("Farklı bir API anahtarı kullan"):
            api_key = st.sidebar.text_input("API Anahtarınız:", type="password", placeholder="sk-...")
    else:
        api_key = st.sidebar.text_input("OpenAI API Anahtarını Gir:", type="password", placeholder="sk-...")



def ai_ile_olustur(prompt: str, key: str) -> str:
    """GPT-5.2 ile metin oluşturur."""
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen profesyonel bir LinkedIn profil danışmanısın. "
                        "Diş hekimliği öğrencileri ve yeni mezunlar için LinkedIn profili oluşturmada uzmansın. "
                        "Verilen bilgilere göre profesyonel, etkileyici ve özgün metinler yaz. "
                        "Kısa, öz ve etkili ol. Emoji kullanımını minimal tut."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ AI Hatası: {str(e)}"


def get_dil_talimat(dil):
    return {
        "🇹🇷 Türkçe": "Türkçe olarak yaz.",
        "🇬🇧 İngilizce": "İngilizce olarak yaz.",
        "🇹🇷🇬🇧 Her İkisi": "Hem Türkçe hem İngilizce versiyonları yaz. Önce Türkçe, sonra '---' ile ayırıp İngilizce yaz."
    }[dil]


def satirdan_listeye(metin):
    return [s.strip() for s in metin.strip().split("\n") if s.strip()]



def headline_promptu(ad_soyad, universite, sinif, klinik_str, diger_str, hedef, dil):
    return f"""LinkedIn profil başlığı (headline) oluştur.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Sınıf: {sinif}
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}
- LinkedIn Hedefi: {hedef}

3 farklı seçenek sun:
1. Sade ve profesyonel
2. İlgi çekici ve yetkinlik odaklı
3. Uluslararası/Global tarz

Her seçenek en fazla 120 karakter olsun (LinkedIn limiti).
{get_dil_talimat(dil)}"""


def about_promptu(ad_soyad, universite, sinif, klinik_str, diger_str, hedef, topluluk_str, sertifika_str, basari_str, dil):
    return f"""LinkedIn 'Hakkında' (About) bölümü için profesyonel bir metin yaz.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Sınıf: {sinif}
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}
- LinkedIn Hedefi: {hedef}
- Topluluklar: {topluluk_str}
- Sertifikalar: {sertifika_str}
- Başarılar: {basari_str}

Kurallar:
- 150-300 kelime arası olsun
- İlk cümle dikkat çekici olsun (hook)
- Kişisel hikaye + profesyonel hedef dengesi kur
- Topluluk ve sertifika bilgilerini doğal bir şekilde entegre et
- Call-to-action ile bitir
- Samimi ama profesyonel ton kullan
{get_dil_talimat(dil)}"""


def experience_promptu(ad_soyad, universite, fakulte, sinif, klinik_str, diger_str, topluluk_str, dil):
    return f"""LinkedIn 'Deneyim' (Experience) bölümü için metin yaz. Bir diş hekimliği öğrencisinin eğitimini profesyonel bir iş deneyimi gibi göster.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Fakülte: {fakulte}
- Sınıf: {sinif}
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}
- Topluluklar: {topluluk_str}

Kurallar:
- Birden fazla deneyim maddesi oluştur (eğitim + topluluk rolleri ayrı ayrı)
- Her deneyim için: Pozisyon, Kurum, Tarih, 3-5 madde açıklama
- Aksiyon fiilleri kullan
- Ölçülebilir başarılar ekle (mümkünse)
{get_dil_talimat(dil)}"""


def education_promptu(ad_soyad, universite, fakulte, sinif, baslangic, bitis, gpa, klinik_str, topluluk_str, basari_str, dil):
    return f"""LinkedIn 'Eğitim' (Education) bölümü için metin yaz.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Fakülte: {fakulte}
- Sınıf: {sinif}
- Eğitim Dönemi: {baslangic} - {bitis}
- GPA: {gpa if gpa else 'Belirtilmemiş'}
- Klinik İlgi Alanları: {klinik_str}
- Topluluklar/Aktiviteler: {topluluk_str}
- Başarılar: {basari_str}

Kurallar:
- LinkedIn Education bölümüne uygun format
- Activities and Societies kısmını doldur
- Description kısmında öğrencilik sürecini özetle
- Kurslar ve ilgi alanlarını entegre et
{get_dil_talimat(dil)}"""


def skills_promptu(klinik_str, diger_str, sinif, dil):
    return f"""Bir diş hekimliği öğrencisi için LinkedIn 'Beceriler' (Skills) bölümüne eklenecek becerileri listele.

Bilgiler:
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}
- Sınıf: {sinif}

Kurallar:
- Tam olarak 15 beceri listele (LinkedIn'de önerilen sayı)
- İlk 5'i en önemli ve üste sabitlenmesi gereken beceriler olsun
- Hem klinik hem transferable (aktarılabilir) beceriler dahil et
- Her becerinin yanına neden önemli olduğunu 1 cümle ile açıkla
- LinkedIn'de aranabilirlik (SEO) için doğru anahtar kelimeleri kullan
{get_dil_talimat(dil)}"""


def sertifika_promptu(sertifika_str, klinik_str, sinif, dil):
    return f"""Bir diş hekimliği öğrencisi için LinkedIn 'Lisanslar ve Sertifikalar' (Licenses & Certifications) bölümü oluştur.

Mevcut Sertifikalar: {sertifika_str}

Bilgiler:
- Klinik İlgi Alanları: {klinik_str}
- Sınıf: {sinif}

Kurallar:
- Mevcut sertifikaları LinkedIn formatına uygun düzenle
- Her sertifika için: Sertifika Adı, Veren Kurum, Tarih
- Ayrıca almayı önerebileceğin 5 sertifika/kurs daha öner (ücretsiz veya uygun fiyatlı)
- Coursera, LinkedIn Learning, ADA, TDB gibi güvenilir kaynaklar öner
{get_dil_talimat(dil)}"""


def gonulluluk_promptu(gonulluluk_str, ad_soyad, universite, klinik_str, dil):
    return f"""LinkedIn 'Gönüllü Deneyim' (Volunteer Experience) bölümü oluştur.

Mevcut Gönüllü Deneyimler: {gonulluluk_str}

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Klinik İlgi Alanları: {klinik_str}

Kurallar:
- Her deneyim için: Rol, Kurum, Tarih, 2-3 madde açıklama
- Toplum sağlığına katkıyı vurgula
- Eğer mevcut deneyim yoksa, diş hekimliği öğrencisine uygun 3 gönüllülük önerisi sun
{get_dil_talimat(dil)}"""


def proje_promptu(proje_str, ad_soyad, universite, klinik_str, diger_str, dil):
    return f"""LinkedIn 'Projeler' (Projects) ve 'Yayınlar' (Publications) bölümü oluştur.

Mevcut Projeler/Yayınlar: {proje_str}

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}

Kurallar:
- Her proje için: Proje Adı, Tarih, İlişkili Kurum, Açıklama (2-3 cümle)
- Ayrıca bir araştırma/proje önerisi sun (öğrenci yapabilecek düzeyde)
{get_dil_talimat(dil)}"""


def recommendation_promptu(ad_soyad, universite, sinif, klinik_str, dil):
    return f"""LinkedIn 'Öneriler' (Recommendations) bölümü için HEM talep mesajları HEM de örnek öneri metinleri yaz.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Sınıf: {sinif}
- Klinik İlgi Alanları: {klinik_str}

Kurallar:
1. Öneri TALEP mesajı yaz (hocana göndermek için) - 2 farklı versiyon (resmi + samimi)
2. Hocanın/mentörün senin hakkında yazabileceği örnek öneri metni oluştur - 2 farklı versiyon
3. Kısa ve etkili ol
{get_dil_talimat(dil)}"""


def mesaj_promptu(ad_soyad, universite, sinif, klinik_ilgi_ilk, hedef, dil):
    return f"""LinkedIn bağlantı isteği mesajı (connection request note) yaz.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Üniversite: {universite}
- Sınıf: {sinif}
- İlgi Alanı: {klinik_ilgi_ilk}
- Hedef: {hedef}

Kurallar:
- En fazla 300 karakter (LinkedIn limiti)
- 3 farklı senaryo için yaz: (1) Profesöre, (2) Sektör profesyoneline, (3) Akrana/öğrenciye
- Her senaryo için 2 versiyon: resmi + samimi
{get_dil_talimat(dil)}"""


def featured_promptu(ad_soyad, klinik_str, diger_str, proje_str, sertifika_str, dil):
    return f"""LinkedIn 'Öne Çıkanlar' (Featured) bölümü için strateji ve içerik önerileri sun.

Bilgiler:
- Ad Soyad: {ad_soyad}
- Klinik İlgi Alanları: {klinik_str}
- Diğer Yetkinlikler: {diger_str}
- Projeler: {proje_str}
- Sertifikalar: {sertifika_str}

Kurallar:
- Featured bölümüne ne eklenmeli? (post, makale, sertifika, proje linki, sunum, vs.)
- 5 farklı içerik önerisi sun ve her birinin neden etkili olduğunu açıkla
- LinkedIn post fikirlerinden 3 örnek taslak yaz (kısa)
{get_dil_talimat(dil)}"""



if st.button("✨ Profilimi Oluştur! ✨", type="primary", use_container_width=True):

    ai_modu = generator_modu == "🤖 AI ile Oluştur (GPT-5.2)"

    if ai_modu and not api_key:
        st.error("❌ AI modu için OpenAI API anahtarı gerekli!")
        st.stop()

    klinik_str = " | ".join(klinik_ilgi) if klinik_ilgi else "Genel Diş Hekimliği"
    diger_str = " & ".join(diger_ilgi) if diger_ilgi else "Klinik Beceriler"
    topluluk_list = satirdan_listeye(topluluklar)
    topluluk_str = ", ".join(topluluk_list) if topluluk_list else "Belirtilmemiş"
    sertifika_list = satirdan_listeye(sertifikalar)
    sertifika_str = ", ".join(sertifika_list) if sertifika_list else "Belirtilmemiş"
    gonulluluk_list = satirdan_listeye(gonulluluk)
    gonulluluk_str = ", ".join(gonulluluk_list) if gonulluluk_list else "Belirtilmemiş"
    proje_list = satirdan_listeye(projeler)
    proje_str = ", ".join(proje_list) if proje_list else "Belirtilmemiş"
    dil_list = satirdan_listeye(diller)
    dil_str = ", ".join(dil_list) if dil_list else "Türkçe - Ana Dil"
    basari_list = satirdan_listeye(basarilar)
    basari_str = ", ".join(basari_list) if basari_list else "Belirtilmemiş"

    if ai_modu:
        st.success("🤖 GPT-5.2 tüm LinkedIn bölümlerini oluşturuyor...")
    else:
        st.success(f"📝 {sinif} seviyesine uygun profesyonel metinler hazırlandı.")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📢 Headline",
        "📝 Hakkında",
        "🎓 Eğitim",
        "💼 Deneyim",
        "🛠️ Beceriler",
        "📜 Sertifikalar",
        "🤝 Gönüllülük",
        "🔬 Projeler",
        "⭐ Öneriler",
        "✉️ Mesajlar & İpuçları"
    ])

    with tab1:
        st.subheader("📢 Profil Başlığın (Headline)")
        st.info("💡 LinkedIn'de adının hemen altında görünen bu alan arama sonuçlarında çıkmanı sağlar. **Max 120 karakter.**")

        if ai_modu:
            with st.spinner("🤖 AI headline oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    headline_promptu(ad_soyad, universite, sinif, klinik_str, diger_str, hedef, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Önerileri")
            st.markdown(ai_result)
            st.divider()
            st.markdown("### 📝 Şablon Seçenekleri")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            st.markdown(f"**1. Sade:** `{fakulte} Öğrencisi @{universite}`")
            st.markdown(f"**2. Odaklı:** `Dth. Adayı | {klinik_str} | {diger_str}`")
            st.markdown(f"**3. Hedef Odaklı:** `{sinif} - {fakulte} @{universite} | {hedef}`")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            if dil_secim == "🇹🇷🇬🇧 Her İkisi":
                st.divider()
                st.markdown("**🇬🇧 English:**")
            st.markdown(f"**1. Clean:** `Dental Student @{universite}`")
            st.markdown(f"**2. Focused:** `Aspiring Dentist | {klinik_str} | {diger_str}`")
            st.markdown(f"**3. Goal-Oriented:** `Future Dentist @{universite} | Passionate about Innovation in Dentistry`")

    with tab2:
        st.subheader("📝 Hikayeni Anlat (About)")
        st.info("💡 LinkedIn'in en önemli bölümü! İlk 3 satır 'Daha fazla gör' tıklanmadan görünür — bu yüzden hook ile başla.")

        if ai_modu:
            with st.spinner("🤖 AI hakkında metni oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    about_promptu(ad_soyad, universite, sinif, klinik_str, diger_str, hedef, topluluk_str, sertifika_str, basari_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.text_area("AI Çıktısı:", value=ai_result, height=350, key="ai_about")
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            topluluk_madde = "\n".join([f"🏛️ {t}" for t in topluluk_list]) if topluluk_list else ""
            basari_madde = "\n".join([f"🏆 {b}" for b in basari_list]) if basari_list else ""

            about_tr = f"""Diş hekimliğinin geleceğini şekillendirmek isteyen bir öğrenci daha burada! 🦷

Ben {ad_soyad}. {universite} {fakulte}'nde {sinif} öğrencisiyim ({baslangic_yili}-{bitis_yili}).

Klinik ilgi alanlarım: {klinik_str}
Bu alanların yanı sıra {diger_str} konularında da kendimi geliştirerek multidisipliner bir bakış açısı kazanmayı hedefliyorum.

{f"Aktif olarak yer aldığım topluluklar:" + chr(10) + topluluk_madde if topluluk_madde else ""}

{f"Başarılarım:" + chr(10) + basari_madde if basari_madde else ""}

LinkedIn'i {hedef.lower()} amacıyla kullanıyorum. Bağlantı kurmaktan çekinme!

📧 {email_goster if email_goster else '[E-posta adresin]'}
{f"🌐 {website}" if website else ""}"""
            st.text_area("🇹🇷 Türkçe:", value=about_tr.strip(), height=350, key="about_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            hedef_en_map = {
                "Staj Bulmak": "finding internship opportunities",
                "Network Genişletmek": "expanding my professional network",
                "Yurt Dışı Olanakları": "exploring international opportunities",
                "Sadece Vitrin Oluşturmak": "building my professional presence"
            }
            about_en = f"""A dental student on a mission to shape the future of dentistry! 🦷

I'm {ad_soyad}, a {sinif} student at {universite} {fakulte} ({baslangic_yili}-{bitis_yili}).

My clinical interests: {klinik_str}
Beyond the clinic, I'm building expertise in {diger_str} to develop a multidisciplinary perspective.

I'm actively using LinkedIn for {hedef_en_map.get(hedef, 'professional growth')}. Let's connect!

📧 {email_goster if email_goster else '[Your email]'}
{f"🌐 {website}" if website else ""}"""
            st.text_area("🇬🇧 English:", value=about_en.strip(), height=300, key="about_en")

    with tab3:
        st.subheader("🎓 Eğitim (Education)")
        st.info("💡 Sadece okul adı yazmak yetmez! Activities, Description ve Courses alanlarını doldur.")

        if ai_modu:
            with st.spinner("🤖 AI eğitim bölümü oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    education_promptu(ad_soyad, universite, fakulte, sinif, baslangic_yili, bitis_yili, gpa, klinik_str, topluluk_str, basari_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.text_area("AI Çıktısı:", value=ai_result, height=350, key="ai_edu")
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            edu_tr = f"""🏫 Okul: {universite}
📚 Bölüm: {fakulte} (Lisans Derecesi)
📅 Dönem: {baslangic_yili} - {bitis_yili} (beklenen)
{f"📊 GPA: {gpa}" if gpa else ""}

📋 Açıklama (Description):
{universite} {fakulte}'nde {sinif} öğrencisi olarak teorik ve klinik eğitimimi sürdürmekteyim. {klinik_str} alanlarında yoğunlaşarak akademik ve klinik yetkinliklerimi geliştiriyorum.

🏛️ Aktiviteler ve Topluluklar (Activities and Societies):
{chr(10).join(['• ' + t for t in topluluk_list]) if topluluk_list else '• [Topluluk adlarını ekle]'}

📖 İlgili Dersler (Relevant Coursework):
• Oral Anatomi ve Histoloji
• Dental Materyaller
• Protetik Diş Hekimliği
• Periodontoloji
• [Kendi derslerini ekle]

{f"🏆 Başarılar:" + chr(10) + chr(10).join(['• ' + b for b in basari_list]) if basari_list else ""}"""
            st.text_area("🇹🇷 Türkçe:", value=edu_tr.strip(), height=400, key="edu_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            edu_en = f"""🏫 School: {universite}
📚 Degree: {fakulte} (Bachelor's Degree)
📅 Period: {baslangic_yili} - {bitis_yili} (expected)
{f"📊 GPA: {gpa}" if gpa else ""}

📋 Description:
Currently a {sinif} student at {universite} {fakulte}, pursuing both theoretical and clinical training with a focus on {klinik_str}.

🏛️ Activities and Societies:
{chr(10).join(['• ' + t for t in topluluk_list]) if topluluk_list else '• [Add your clubs and societies]'}

📖 Relevant Coursework:
• Oral Anatomy and Histology
• Dental Materials
• Prosthodontics
• Periodontology
• [Add your courses]"""
            st.text_area("🇬🇧 English:", value=edu_en.strip(), height=350, key="edu_en")

    with tab4:
        st.subheader("💼 Deneyim (Experience)")
        st.info("💡 Öğrenciliğini bir iş deneyimi gibi anlat! Her topluluk rolü ayrı bir deneyim maddesi olabilir.")

        if ai_modu:
            with st.spinner("🤖 AI deneyim oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    experience_promptu(ad_soyad, universite, fakulte, sinif, klinik_str, diger_str, topluluk_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.text_area("AI Çıktısı:", value=ai_result, height=400, key="ai_exp")
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            exp_tr = f"""━━━ DENEYİM 1 ━━━
💼 Pozisyon: Diş Hekimliği Öğrencisi
🏢 Kurum: {universite} - {fakulte}
📅 Tarih: {baslangic_yili} - Devam ediyor

• {universite} bünyesinde teorik ve klinik diş hekimliği eğitimi almaktayım.
• {klinik_str} alanlarında güncel literatürü takip ediyor, vaka analizlerine katılıyorum.
• Preklinik laboratuvar çalışmalarında el becerisi ve materyal bilgisi üzerine yoğunlaşıyorum.
• [Klinik staj deneyimlerini ekle]"""

            for i, topluluk in enumerate(topluluk_list[:3], 2):
                exp_tr += f"""

━━━ DENEYİM {i} ━━━
💼 Pozisyon: Aktif Üye / [Görevini yaz]
🏢 Kurum: {topluluk}
📅 Tarih: [Başlangıç] - Devam ediyor

• [Bu toplulukta yaptıklarını madde madde yaz]
• [Organize ettiğin etkinlikler, katıldığın projeler]
• [Kazandığın beceriler ve katkıların]"""

            st.text_area("🇹🇷 Türkçe:", value=exp_tr.strip(), height=500, key="exp_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            exp_en = f"""━━━ EXPERIENCE 1 ━━━
💼 Position: Dental Student
🏢 Organization: {universite} - {fakulte}
📅 Date: {baslangic_yili} - Present

• Pursuing comprehensive dental education including theoretical and clinical training.
• Actively following current literature in {klinik_str} and participating in case analyses.
• Developing manual dexterity and materials science expertise in preclinical labs.
• [Add clinical rotation experiences]"""

            for i, topluluk in enumerate(topluluk_list[:3], 2):
                exp_en += f"""

━━━ EXPERIENCE {i} ━━━
💼 Position: Active Member / [Your Role]
🏢 Organization: {topluluk}
📅 Date: [Start] - Present

• [Describe your contributions]
• [Events organized, projects participated in]
• [Skills gained and impact made]"""

            st.text_area("🇬🇧 English:", value=exp_en.strip(), height=500, key="exp_en")

    with tab5:
        st.subheader("🛠️ Beceriler (Skills & Endorsements)")
        st.info("💡 5+ beceri ekle — bu, bağlantı isteği alma oranını **3 kat** artırır! İlk 3'ü profilinde doğrudan görünür.")

        if ai_modu:
            with st.spinner("🤖 AI beceri listesi oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    skills_promptu(klinik_str, diger_str, sinif, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Önerileri")
            st.markdown(ai_result)
            st.divider()
            st.markdown("### 📝 Şablon Beceri Listesi")

        klinik_beceriler_tr = [
            "Oral Muayene ve Teşhis", "Dental Radyografi", "Restoratif Diş Hekimliği",
            "Endodontik Tedavi", "Periodontoloji", "Protetik Diş Hekimliği",
            "Dental Anatomi", "Enfeksiyon Kontrolü", "Hasta İletişimi",
            "Preklinik Laboratuvar Becerileri"
        ]
        klinik_beceriler_en = [
            "Oral Examination & Diagnosis", "Dental Radiography", "Restorative Dentistry",
            "Endodontic Treatment", "Periodontology", "Prosthodontics",
            "Dental Anatomy", "Infection Control", "Patient Communication",
            "Preclinical Laboratory Skills"
        ]
        diger_beceriler_tr = [
            "Akademik Araştırma", "Veri Analizi", "Microsoft Office",
            "Sunum Becerileri", "Takım Çalışması", "Zaman Yönetimi",
            "Proje Yönetimi", "Sosyal Medya", "Dental Fotoğrafçılık"
        ]
        diger_beceriler_en = [
            "Academic Research", "Data Analysis", "Microsoft Office",
            "Presentation Skills", "Teamwork", "Time Management",
            "Project Management", "Social Media", "Dental Photography"
        ]

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            st.markdown("**🔬 Klinik Beceriler (üste sabitle):**")
            for i, b in enumerate(klinik_beceriler_tr, 1):
                st.markdown(f"{i}. ✅ {b}")
            st.markdown("**💡 Transferable Beceriler:**")
            for i, b in enumerate(diger_beceriler_tr, 1):
                st.markdown(f"{i}. ✅ {b}")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            if dil_secim == "🇹🇷🇬🇧 Her İkisi":
                st.divider()
            st.markdown("**🔬 Clinical Skills (pin to top):**")
            for i, b in enumerate(klinik_beceriler_en, 1):
                st.markdown(f"{i}. ✅ {b}")
            st.markdown("**💡 Transferable Skills:**")
            for i, b in enumerate(diger_beceriler_en, 1):
                st.markdown(f"{i}. ✅ {b}")

    with tab6:
        st.subheader("📜 Lisanslar & Sertifikalar (Licenses & Certifications)")
        st.info("💡 Tamamladığın her kursu ve sertifikayı ekle. LinkedIn Learning sertifikaları otomatik eklenir!")

        if ai_modu:
            with st.spinner("🤖 AI sertifika bölümü oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    sertifika_promptu(sertifika_str, klinik_str, sinif, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.markdown(ai_result)
            st.divider()
            st.markdown("### 📝 Şablon & Öneriler")

        if sertifika_list:
            st.markdown("**📜 Senin Sertifikaların:**")
            for s in sertifika_list:
                st.markdown(f"""
- **{s}**
  - Veren Kurum: [Kurumu ekle]
  - Tarih: [Tarihi ekle]
  - Kimlik No: [Varsa ekle]
""")

        st.markdown("**💡 Diş Hekimliği Öğrencileri İçin Önerilen Sertifikalar:**")
        onerilen = [
            ("Temel Yaşam Desteği (BLS/CPR)", "Kızılay / AHA"),
            ("Dental Photography Fundamentals", "Coursera / Udemy"),
            ("Infection Control in Dentistry", "ADA / Coursera"),
            ("CAD/CAM in Dentistry", "LinkedIn Learning"),
            ("Scientific Writing & Research Methods", "Coursera"),
            ("Excel / Data Analysis for Healthcare", "LinkedIn Learning"),
            ("İlk Yardım Sertifikası", "Kızılay"),
            ("Radyasyon Güvenliği", "TAEK / Üniversite"),
        ]
        for kurs, kurum in onerilen:
            st.markdown(f"- ✅ **{kurs}** — *{kurum}*")

    with tab7:
        st.subheader("🤝 Gönüllü Deneyim (Volunteer Experience)")
        st.info("💡 Gönüllülük bölümü profilini insancıllaştırır ve toplum sağlığına verdiğin değeri gösterir.")

        if ai_modu:
            with st.spinner("🤖 AI gönüllülük bölümü oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    gonulluluk_promptu(gonulluluk_str, ad_soyad, universite, klinik_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.text_area("AI Çıktısı:", value=ai_result, height=300, key="ai_vol")
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        if gonulluluk_list:
            for g in gonulluluk_list:
                st.markdown(f"""**🤝 {g}**
- Rol: Gönüllü Diş Hekimliği Öğrencisi
- Tarih: [Tarihi ekle]
- Açıklama: [Yaptıklarını 2-3 madde ile anlat]
""")
        else:
            st.warning("Henüz gönüllü deneyim girmedin. İşte bazı öneriler:")

        st.markdown("**💡 Öğrenciler İçin Gönüllülük Fikirleri:**")
        fikirler = [
            "🏫 Okullarda Ağız Sağlığı Eğitimi (diş fırçalama tekniği anlatımı)",
            "🏥 Toplum Sağlığı Taramaları (belediye iş birlikleri)",
            "📚 Akran Mentorluk Programı (alt sınıflara destek)",
            "🌍 IFMSA / IADS Uluslararası Değişim Programları",
            "🦷 Diş Hekimleri Günü Etkinlikleri / Farkındalık Kampanyaları"
        ]
        for f in fikirler:
            st.markdown(f"- {f}")

    with tab8:
        st.subheader("🔬 Projeler & Yayınlar (Projects & Publications)")
        st.info("💡 Araştırma projeleri ve vaka çalışmaları profilini akademik açıdan güçlendirir.")

        if ai_modu:
            with st.spinner("🤖 AI proje bölümü oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    proje_promptu(proje_str, ad_soyad, universite, klinik_str, diger_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.text_area("AI Çıktısı:", value=ai_result, height=300, key="ai_proj")
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        if proje_list:
            for p in proje_list:
                st.markdown(f"""**🔬 {p}**
- İlişkili Kurum: {universite}
- Tarih: [Tarihi ekle]
- Açıklama: [2-3 cümle ile projeyi anlat]
- URL: [Varsa link ekle]
""")
        else:
            st.warning("Henüz proje girmedin.")

        st.markdown("**💡 Öğrenciler İçin Proje Fikirleri:**")
        proje_fikirleri = [
            "🤖 Yapay Zeka ile Dental Röntgen Analizi (Python + Deep Learning)",
            "😁 Dijital Gülüş Tasarımı (DSD) Vaka Çalışması",
            "📊 Ağız Sağlığı Farkındalığı Anketi ve Veri Analizi",
            "🦷 3D Baskı ile Dental Model Üretimi",
            "📱 Hasta Takip Uygulaması Prototipi",
            "📖 Sistematik Derleme / Literatür Taraması"
        ]
        for f in proje_fikirleri:
            st.markdown(f"- {f}")

    with tab9:
        st.subheader("⭐ Öneriler (Recommendations)")
        st.info("💡 Kişisel tanıklıklar profilinin güvenilirliğini artırır. En az 2-3 öneri almayı hedefle!")

        if ai_modu:
            with st.spinner("🤖 AI öneri metinleri oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    recommendation_promptu(ad_soyad, universite, sinif, klinik_str, dil_secim),
                    api_key
                )
            st.markdown("### 🤖 AI Tarafından Oluşturulan")
            st.markdown(ai_result)
            st.divider()
            st.markdown("### 📝 Şablon Versiyonu")

        st.markdown("#### 📨 Öneri Talep Mesajı (Hocana Gönder)")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            rec_req_tr = f"""Sayın [Hocanın Adı],

{universite} {fakulte}'ndeki eğitimim süresince derslerinizden ve rehberliğinizden çok faydalandım. LinkedIn profilim için kısa bir öneri yazmanız mümkün olur mu?

Özellikle [klinik beceri / araştırma / proje] konusundaki gözlemlerinizi paylaşmanız benim için çok değerli olurdu.

Şimdiden teşekkür ederim.
Saygılarımla,
{ad_soyad}"""
            st.text_area("🇹🇷 Talep Mesajı:", value=rec_req_tr, height=200, key="rec_req_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            rec_req_en = f"""Dear Professor [Name],

I have greatly benefited from your guidance during my studies at {universite}. Would you be willing to write a brief recommendation for my LinkedIn profile?

I would especially appreciate your perspective on [clinical skills / research / specific project].

Thank you in advance.
Best regards,
{ad_soyad}"""
            st.text_area("🇬🇧 Request Message:", value=rec_req_en, height=200, key="rec_req_en")

        st.divider()
        st.markdown("#### ✍️ Hocanın Yazabileceği Örnek Öneri")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            rec_sample_tr = f"""{ad_soyad}'ı {universite} {fakulte}'ndeki eğitimi süresince yakından tanıma fırsatım oldu. Özellikle {klinik_str} alanındaki merakı ve öğrenme azmi dikkat çekicidir. Klinik çalışmalarında titiz, hasta iletişiminde empatik bir yaklaşım sergiler. Akademik potansiyelinin yanı sıra takım çalışmasına yatkınlığı ile de öne çıkan bir öğrencidir. Gelecekte mesleğine önemli katkılar sunacağına inancım tamdır."""
            st.text_area("🇹🇷 Örnek Öneri:", value=rec_sample_tr, height=150, key="rec_sample_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            rec_sample_en = f"""I had the pleasure of teaching {ad_soyad} at {universite}. Their passion for {klinik_str} is evident in their meticulous approach to clinical work and dedication to continuous learning. Beyond technical skills, they demonstrate excellent patient communication and a collaborative spirit. I am confident they will make significant contributions to the dental profession."""
            st.text_area("🇬🇧 Sample Recommendation:", value=rec_sample_en, height=150, key="rec_sample_en")

    with tab10:
        st.subheader("✉️ Bağlantı Mesajları & Profil İpuçları")

        st.markdown("### ✉️ Bağlantı İsteği Mesajları (Connection Request)")
        st.warning("LinkedIn bağlantı notu max 300 karakter! 'Not Ekle' diyerek kullanabilirsin.")

        klinik_ilgi_ilk = klinik_ilgi[0] if klinik_ilgi else "diş hekimliği"

        if ai_modu:
            with st.spinner("🤖 AI mesajlar oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    mesaj_promptu(ad_soyad, universite, sinif, klinik_ilgi_ilk, hedef, dil_secim),
                    api_key
                )
            st.markdown("#### 🤖 AI Önerileri")
            st.text_area("AI Çıktısı:", value=ai_result, height=250, key="ai_msg")
            st.divider()
            st.markdown("#### 📝 Şablon Versiyonları")

        if dil_secim in ["🇹🇷 Türkçe", "🇹🇷🇬🇧 Her İkisi"]:
            msg1_tr = f"""Sayın [İsim], ben {universite} {sinif} öğrencisi {ad_soyad}. {klinik_ilgi_ilk} alanındaki çalışmalarınızı takip ediyorum. Bağlantıda kalmak isterim. Saygılarımla."""
            msg2_tr = f"""Merhaba! Ben {ad_soyad}, {universite}'de diş hekimliği okuyorum. {hedef.lower()} konusunda fikirlerinizden yararlanmak isterim. Tanışmak güzel olur! 😊"""
            msg3_tr = f"""Selam! Ben de {fakulte} öğrencisiyim. Profilinizi inceledim, benzer ilgi alanlarımız var. Bağlantı kuralım mı? 🦷"""
            st.text_area("🇹🇷 Profesöre:", value=msg1_tr, height=100, key="msg1_tr")
            st.text_area("🇹🇷 Sektör Profesyoneline:", value=msg2_tr, height=100, key="msg2_tr")
            st.text_area("🇹🇷 Akrana:", value=msg3_tr, height=100, key="msg3_tr")

        if dil_secim in ["🇬🇧 İngilizce", "🇹🇷🇬🇧 Her İkisi"]:
            msg1_en = f"""Dear [Name], I'm {ad_soyad}, a dental student at {universite}. I admire your work in {klinik_ilgi_ilk} and would love to connect. Best regards."""
            msg2_en = f"""Hi! I'm {ad_soyad} from {universite}. I'm exploring opportunities in {klinik_ilgi_ilk} and would appreciate connecting with professionals like you."""
            msg3_en = f"""Hey! Fellow dental student here 🦷 Noticed we share similar interests. Let's connect and exchange ideas!"""
            st.text_area("🇬🇧 To Professor:", value=msg1_en, height=100, key="msg1_en")
            st.text_area("🇬🇧 To Professional:", value=msg2_en, height=100, key="msg2_en")
            st.text_area("🇬🇧 To Peer:", value=msg3_en, height=100, key="msg3_en")

        st.divider()

        st.markdown("### 🌟 Öne Çıkanlar (Featured Section)")
        st.info("💡 Profilinin en görünür bölümlerinden biri! Post, makale, sertifika ve proje linkleri ekleyebilirsin.")

        if ai_modu:
            with st.spinner("🤖 AI Featured önerileri oluşturuyor..."):
                ai_result = ai_ile_olustur(
                    featured_promptu(ad_soyad, klinik_str, diger_str, proje_str, sertifika_str, dil_secim),
                    api_key
                )
            st.markdown("#### 🤖 AI Önerileri")
            st.markdown(ai_result)
            st.divider()

        st.markdown("**Featured'a Ekle:**")
        featured_onerileri = [
            "📸 En iyi dental fotoğrafın veya klinik çalışma görselin",
            "📝 LinkedIn'de yazdığın bir makale veya paylaşım",
            "📜 Tamamladığın en önemli sertifika",
            "🔬 Araştırma poster veya sunum dosyan",
            "🎤 Katıldığın bir konferans/webinar özeti",
            "📊 Bir vaka çalışması veya proje sonuçları",
        ]
        for f in featured_onerileri:
            st.markdown(f"- {f}")

        st.divider()

        st.markdown("### 📸 Profil Fotoğrafı İpuçları")
        st.markdown("""
LinkedIn'in kendi araştırmasına göre profil fotoğrafı olan hesaplar **14 kat daha fazla** görüntülenir!

**✅ Yapılması Gerekenler:**
- Yüzün fotoğrafın **%60'ını** kaplasın
- Güncel bir fotoğraf kullan (son 1-2 yıl)
- Profesyonel kıyafet giy (beyaz önlük ideal! 🥼)
- Doğal ışıkta çekim yap
- Gözlerinle gülümse 😊
- Sade, düz bir arka plan seç

**❌ Yapılmaması Gerekenler:**
- Selfie veya grup fotoğrafından kırpma
- Güneş gözlüğü veya şapka
- Aşırı filtre veya düzenleme
- Çok eski fotoğraflar
- Resmi olmayan ortam fotoğrafları
""")

        st.divider()

        st.markdown("### 🖼️ Kapak Fotoğrafı (Banner) İpuçları")
        st.markdown(f"""
- **Boyut:** 1584 x 396 piksel
- Üniversite logosu + fakülte görseli kullanabilirsin
- Canva'da ücretsiz LinkedIn banner şablonları var
- İlgi alanlarını yansıtan bir görsel seç (dental ekipman, gülümseme, vs.)
- İsim ve kısa slogan ekleyebilirsin: *"{ad_soyad} | {fakulte} @{universite}"*
""")

        st.divider()

        st.markdown("### 🗣️ Dil Bilgisi (Languages)")
        if dil_list:
            for d in dil_list:
                st.markdown(f"- 🗣️ {d}")
        else:
            st.markdown("- Türkçe - Ana Dil\n- İngilizce - [Seviyeni ekle]")

        st.divider()

        st.markdown("### 👥 Takip Edilmesi Önerilen Hesaplar")
        st.markdown("""
LinkedIn'de sektör liderlerini takip etmek, feedinde kaliteli içerik görmeni sağlar:

- 🦷 **ADA (American Dental Association)**
- 🦷 **FDI World Dental Federation**
- 🇹🇷 **Türk Diş Hekimleri Birliği (TDB)**
- 📚 **Journal of Dental Research**
- 🤖 **AI in Dentistry** (hashtag: #AIinDentistry)
- 🎓 Kendi üniversitenin resmi LinkedIn sayfası
- 👨‍⚕️ Alanında tanınmış profesörler ve klinisyenler
""")

else:
    st.info("👈 Sol menüden bilgilerini gir ve sihrin gerçekleşmesini bekle!")

st.markdown("---")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption("Developed by **Mahir Yusuf Açan** (Data Scientist & Dental Student)")
with col_f2:
    if generator_modu == "🤖 AI ile Oluştur (GPT-5.2)":
        st.caption("Powered by **Streamlit** & **OpenAI GPT-5.2** 🤖")
    else:
        st.caption("Powered by **Streamlit** ⚡")
