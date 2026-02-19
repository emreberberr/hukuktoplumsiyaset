# Streamlit + Google Sheets (Terminalsiz, Tıklama Odaklı Kurulum)

Bu rehberde terminal komutu zorunlu degildir.

## 1) Yerelde tek tikla test

1. `BASLAT_STREAMLIT.bat` dosyasina cift tiklayin.
2. Tarayicida `http://localhost:8501` acilir.
3. Google Sheets baglantisini ayarlamadiysaniz sayfada uyari gorursunuz, normaldir.

## 2) Google Sheets dosyasini olustur

1. `sheets.google.com` acin.
2. `Blank` ile yeni bir tablo olusturun.
3. Adini ornegin `Sunum Kayitlari` yapin.
4. URL'den Sheet ID'yi kopyalayin.
   Ornek URL:
   `https://docs.google.com/spreadsheets/d/1AbCdEfGh.../edit#gid=0`
   Burada ID: `1AbCdEfGh...`

## 3) Google Service Account olustur (tamamen tiklama ile)

1. `console.cloud.google.com` girin.
2. Ustten `Select project` > `New Project` > proje olustur.
3. Sol menude `APIs & Services` > `Library`:
   - `Google Sheets API` -> `Enable`
   - `Google Drive API` -> `Enable`
4. Sol menude `APIs & Services` > `Credentials` > `Create Credentials` > `Service account`.
5. Bir ad verin (`streamlit-sheets-bot` gibi) > `Create and continue` > `Done`.
6. Service account listesinde olusturdugunu ac.
7. `Keys` sekmesi > `Add key` > `Create new key` > `JSON` > `Create`.
8. JSON dosyasi bilgisayarina iner.

## 4) Google Sheet'i service account ile paylas

1. İndirdigin JSON dosyasini Not Defteri ile ac.
2. `client_email` alanini kopyala (`...@...gserviceaccount.com`).
3. Google Sheet'e don, `Share` butonu.
4. Bu e-postayi ekle ve `Editor` izni ver.

## 5) GitHub'a kod yukle (terminalsiz)

1. `github.com` hesabinla gir.
2. `New repository` olustur (ornek: `sunum-secim-app`).
3. `Add file` > `Upload files`.
4. Bu klasorden su dosyalari surukleyip birak:
   - `streamlit_app.py`
   - `requirements.txt`
   - `.streamlit/secrets.toml.template`
   - `README_STREAMLIT_TIKLAMA_REHBERI.md`
5. `Commit changes` tikla.

## 6) Streamlit Community Cloud'a deploy et

1. `share.streamlit.io` gir ve GitHub ile login ol.
2. `New app` tikla.
3. Repository: az once olusturdugun repo.
4. Branch: `main`.
5. Main file path: `streamlit_app.py`.
6. `Deploy` tikla.

## 7) Secrets alanini doldur

1. App acildiktan sonra sag ust `Manage app` > `Settings` > `Secrets`.
2. `.streamlit/secrets.toml.template` dosyasini ac.
3. Asagidaki gibi gercek degerlerle doldurup Secrets kutusuna yapistir:
   - `SHEET_ID`: Google Sheet ID
   - `WORKSHEET_NAME`: `submissions` (degistirebilirsin)
   - `ADMIN_PASSWORD`: sana ozel sifre (opsiyonel ama onerilir)
   - `[gcp_service_account]` blogu: indirdigin JSON'daki alanlar
4. `Save` tikla.
5. App otomatik yeniden baslar.

## 8) Linki ogrencilerle paylas

- App linkin su formatta olur:
  `https://<app-adi>.streamlit.app`
- Ogrenciler formu doldurdukca veriler dogrudan Google Sheets'e yazar.

## 9) Verileri nereden gorursun?

1. Dogrudan Google Sheet'ten.
2. Uygulama icinde yonetici panelinden (sifreyi dogru girersen CSV indirebilirsin).

## 10) Notlar

- Bu cozum tamamen ucretsiz katmanlarla calisir.
- Cok nadir de olsa ayni anda iki kisinin gonderiminde kota yarisi olabilir; uygulama gonderim aninda ikinci kez kontrol eder.
- En guvenli takip icin asil kaynak her zaman Google Sheets tablosudur.
