import re
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sunum Konusu ve Tarih Seçimi", layout="centered")

MAX_CAPACITY_PER_DATE = 2
OTHER_OPTION_LABEL = "Diğer (Lütfen kendi ödev başlığınızı belirtiniz)"

COURSE_INFO = {
    "course_name": "Hukuk, Toplum ve Siyaset",
    "lecturer": "Dr. Öğretim Üyesi Y. Emre Berber",
    "institution": "Ankara Yıldırım Beyazıt Üniversitesi – Sosyal Bilimler Enstitüsü – Kamu Hukuku Tezsiz Yüksek Lisans Programı",
    "instruction": (
        "Lütfen listeden bir ödev konusu ve uygun bir sunum tarihi seçiniz. "
        "Her hafta en fazla iki sunum yapılabilmektedir. "
        'Kendi konunuzu belirlemek isterseniz ilgili kategorideki "Diğer" seçeneğini işaretleyerek başlığınızı yazabilirsiniz.'
    ),
    "note": "Önemli Not: Kendi belirlediğiniz konular, dersin hocasının onayından sonra geçerli kabul edilecektir.",
}

CATEGORY_LABELS = {
    "hukukun_ardina_bakmak": "Kategori 1 (Hukukun Ardına Bakmak)",
    "hukukun_toplumsal_sinirlari": "Kategori 2 (Hukukun Toplumsal Sınırları)",
}

TOPICS_BY_CATEGORY = {
    "hukukun_ardina_bakmak": [
        "Kira Artışında %25 Sınırı ve Tahliye Zorlukları",
        "Uber ve/veya Martı Hakkındaki Hukuki Süreç",
        "Süresiz Nafaka Düzenlemesi",
        "İmar Barışı Düzenlemeleri",
        "Emeklilikte Yaşa Takılanlar (EYT) Düzenlemesi",
        'Özelleştirilen Otoyol ve Köprülerdeki "Geçiş Garantisi" Uygulamaları',
        '"Uyutma" Tartışmaları Bağlamında Hayvan Hakları Kanunu',
        "İş Hukukunda Dava Şartı Arabuluculuk",
        "AirBnB gibi Online Platformlar Bağlamında Turizm Amaçlı Konut Kiralama Düzenlemesi",
        "Kamuda Tıbbi Malpraktis ve Rücu Rejimi",
        "Grev Erteleme Rejimi",
        "Başörtüsü Yasağı",
        "2932 Sayılı Kanun ve Dil Yasakları",
        "Taşınmaz Alımı Yoluyla Vatandaşlık Kazanılması Düzenlemesi",
        "Ortak Sağlık ve Güvenlik Birimleri Modeli",
        "Kıdem Tazminatı Kurumu",
        "Konut ve Çatılı İşyeri Kirasında 10 Yıllık Uzama Süresi (TBK 347)",
        "Seçim Barajı (%7)",
        "6284 Sayılı Kanun Kapsamında Uzaklaştırma Kararları",
        "GIG Ekonomisi (Esnaf Kurye Modeli) ve Çalışanların İşçi Niteliği Sorunu",
        OTHER_OPTION_LABEL,
    ],
    "hukukun_toplumsal_sinirlari": [
        "Ötenazi",
        "Uyuşturucu",
        "Kürtaj",
        "Taşıyıcı annelik",
        "Müstehcen yayınlar",
        "Kumar",
        "Fuhuş",
        "Ensest",
        "Dilencilik",
        OTHER_OPTION_LABEL,
    ],
}

ACTIVE_DATES = [
    {"value": "2026-03-25", "label": "25 Mart 2026"},
    {"value": "2026-04-15", "label": "15 Nisan 2026"},
    {"value": "2026-04-22", "label": "22 Nisan 2026"},
    {"value": "2026-04-29", "label": "29 Nisan 2026"},
    {"value": "2026-05-06", "label": "6 Mayıs 2026"},
    {"value": "2026-05-13", "label": "13 Mayıs 2026"},
]
ACTIVE_DATE_SET = {item["value"] for item in ACTIVE_DATES}
ACTIVE_DATE_LABELS = {item["value"]: item["label"] for item in ACTIVE_DATES}

BLOCKED_DATES = [
    {"value": "2026-04-01", "label": "1 Nisan 2026", "reason": "Vize haftası"},
    {"value": "2026-04-08", "label": "8 Nisan 2026", "reason": "Vize haftası"},
    {"value": "2026-05-20", "label": "20 Mayıs 2026", "reason": "Son hafta"},
]

NAME_PATTERN = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü\s.'-]+$")

SHEET_RECORD_KEYS = [
    "timestamp",
    "ogrenci_adi_soyadi",
    "kategori_anahtar",
    "kategori",
    "secilen_konu",
    "ozel_baslik",
    "nihai_baslik",
    "sunum_tarihi_iso",
    "sunum_tarihi",
    "onay_gerekli",
]

LEGACY_SHEET_HEADERS = SHEET_RECORD_KEYS.copy()

SHEET_HEADERS = [
    "Kayit Zamani",
    "Ogrenci Adi Soyadi",
    "Kategori Anahtari",
    "Kategori",
    "Listeden Secilen Konu",
    "Ozel Baslik (Varsa)",
    "Nihai Odev Basligi",
    "Sunum Tarihi (ISO)",
    "Sunum Tarihi",
    "Onay Gerekli mi?",
]

ADMIN_COLUMN_NAMES = dict(zip(SHEET_RECORD_KEYS, SHEET_HEADERS))


def apply_sheet_presentation(worksheet):
    sheet_id = worksheet._properties.get("sheetId")
    if sheet_id is None:
        return

    requests = [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.93, "green": 0.96, "blue": 0.99},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 10,
                }
            }
        },
    ]

    # Teknik alanlar gizlenir; ana okunur alanlar gorunur kalir.
    technical_columns = [2, 4, 5, 7]
    for column_index in technical_columns:
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index,
                        "endIndex": column_index + 1,
                    },
                    "properties": {"hiddenByUser": True},
                    "fields": "hiddenByUser",
                }
            }
        )

    worksheet.spreadsheet.batch_update({"requests": requests})


@st.cache_resource(show_spinner=False)
def get_worksheet():
    if "gcp_service_account" not in st.secrets or "SHEET_ID" not in st.secrets:
        raise RuntimeError("Eksik Streamlit secrets ayarı")

    credentials_info = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(st.secrets["SHEET_ID"])
    worksheet_name = st.secrets.get("WORKSHEET_NAME", "submissions")

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=2000, cols=20)

    first_row = worksheet.row_values(1)
    if not first_row:
        worksheet.update("A1:J1", [SHEET_HEADERS])
    elif first_row == LEGACY_SHEET_HEADERS:
        worksheet.update("A1:J1", [SHEET_HEADERS])
    try:
        apply_sheet_presentation(worksheet)
    except Exception:
        pass

    return worksheet


def get_records(worksheet):
    values = worksheet.get_all_values()
    if not values:
        return []

    headers = values[0]
    rows = values[1:]

    if headers == SHEET_HEADERS or headers == LEGACY_SHEET_HEADERS:
        records = []
        for row in rows:
            padded = row + [""] * max(0, len(SHEET_RECORD_KEYS) - len(row))
            records.append(dict(zip(SHEET_RECORD_KEYS, padded[: len(SHEET_RECORD_KEYS)])))
        return records

    normalized = []
    for row in rows:
        padded = row + [""] * max(0, len(SHEET_RECORD_KEYS) - len(row))
        item = {}
        for index, key in enumerate(SHEET_RECORD_KEYS):
            item[key] = padded[index] if index < len(padded) else ""
        normalized.append(item)
    return normalized


def calculate_date_counts(records):
    counter = Counter()
    for record in records:
        date_value = record.get("sunum_tarihi_iso", "")
        if date_value in ACTIVE_DATE_SET:
            counter[date_value] += 1
    return counter


def validate_form(student_name, category_key, topic, custom_topic, selected_date):
    errors = []

    if not student_name:
        errors.append("Öğrenci adı ve soyadı zorunludur.")
    elif len(student_name) > 120:
        errors.append("Öğrenci adı ve soyadı en fazla 120 karakter olabilir.")
    elif not NAME_PATTERN.fullmatch(student_name):
        errors.append("Öğrenci adı ve soyadı alanı yalnızca metin içermelidir.")

    if category_key not in CATEGORY_LABELS:
        errors.append("Lütfen geçerli bir kategori seçiniz.")

    valid_topics = TOPICS_BY_CATEGORY.get(category_key, [])
    if topic not in valid_topics:
        errors.append("Lütfen seçtiğiniz kategoriye uygun geçerli bir ödev konusu seçiniz.")

    if topic == OTHER_OPTION_LABEL:
        if not custom_topic:
            errors.append('"Diğer" seçildiğinde özel ödev başlığı zorunludur.')
        elif len(custom_topic) > 250:
            errors.append("Özel ödev başlığı en fazla 250 karakter olabilir.")

    if selected_date not in ACTIVE_DATE_SET:
        errors.append("Lütfen açık olan tarihlerden birini seçiniz.")

    return errors


def date_option_label(date_value, count_map):
    label = ACTIVE_DATE_LABELS[date_value]
    used = count_map.get(date_value, 0)
    remaining = max(MAX_CAPACITY_PER_DATE - used, 0)
    return f"{label} - Kalan kontenjan: {remaining}"


def format_availability_table(count_map):
    rows = []

    for item in ACTIVE_DATES:
        used = count_map.get(item["value"], 0)
        status = "Dolu" if used >= MAX_CAPACITY_PER_DATE else "Müsait"
        rows.append(
            {
                "Tarih": item["label"],
                "Durum": status,
                "Detay": f"{used}/{MAX_CAPACITY_PER_DATE} dolu",
            }
        )

    for item in BLOCKED_DATES:
        rows.append(
            {
                "Tarih": item["label"],
                "Durum": "Kapalı",
                "Detay": item["reason"],
            }
        )

    return pd.DataFrame(rows)


def show_setup_error(error):
    st.error("Google Sheets bağlantısı kurulamadı.")
    st.info(
        "App açıldıktan sonra Streamlit Cloud > App settings > Secrets bölümüne secrets değerlerini ekleyin. "
        "Şablon dosyası: `.streamlit/secrets.toml.template`"
    )
    st.caption(f"Teknik detay: {error}")


def show_header():
    st.title(COURSE_INFO["course_name"])
    st.markdown(f"**Hoca:** {COURSE_INFO['lecturer']}")
    st.markdown(f"**Kurum:** {COURSE_INFO['institution']}")
    st.write(COURSE_INFO["instruction"])
    st.warning(COURSE_INFO["note"])


def show_admin_panel(records):
    admin_password = st.secrets.get("ADMIN_PASSWORD", "")
    if not admin_password:
        return

    with st.expander("Yönetici Paneli (Opsiyonel)"):
        entered = st.text_input("Yönetici şifresi", type="password")

        if not entered:
            st.caption("Kayıtları görüntülemek için şifre girin.")
            return

        if entered != admin_password:
            st.error("Şifre hatalı.")
            return

        if not records:
            st.info("Henüz kayıt yok.")
            return

        table = pd.DataFrame(records).rename(columns=ADMIN_COLUMN_NAMES)
        ordered_columns = [col for col in SHEET_HEADERS if col in table.columns]
        if ordered_columns:
            table = table[ordered_columns]
        st.dataframe(table, use_container_width=True)

        csv_data = table.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "CSV indir",
            data=csv_data,
            file_name="sunum_kayitlari.csv",
            mime="text/csv",
            use_container_width=True,
        )


def main():
    show_header()

    try:
        worksheet = get_worksheet()
    except Exception as error:
        show_setup_error(error)
        return

    records = get_records(worksheet)
    count_map = calculate_date_counts(records)

    st.subheader("Sunum Kaydı")
    student_name = st.text_input("Öğrenci Adı ve Soyadı *", max_chars=120).strip()

    category_options = [""] + list(CATEGORY_LABELS.keys())
    category_key = st.selectbox(
        "Kategori Seçimi *",
        options=category_options,
        format_func=lambda x: "Kategori seçiniz" if x == "" else CATEGORY_LABELS[x],
    )

    topic_options = TOPICS_BY_CATEGORY.get(category_key, [])
    topic = st.selectbox(
        "Ödev Konusu Seçimi *",
        options=[""] + topic_options,
        format_func=lambda x: "Ödev konusu seçiniz" if x == "" else x,
        disabled=(category_key == ""),
    )

    custom_topic = ""
    if topic == OTHER_OPTION_LABEL:
        custom_topic = st.text_input("Özel Ödev Başlığı *", max_chars=250).strip()

    open_dates = [
        date_item["value"]
        for date_item in ACTIVE_DATES
        if count_map.get(date_item["value"], 0) < MAX_CAPACITY_PER_DATE
    ]

    selected_date = st.selectbox(
        "Sunum Tarihi *",
        options=[""] + open_dates,
        format_func=lambda x: "Tarih seçiniz" if x == "" else date_option_label(x, count_map),
    )

    submitted = st.button("Kaydı Tamamla", use_container_width=True)

    if submitted:
        errors = validate_form(student_name, category_key, topic, custom_topic, selected_date)

        latest_records = get_records(worksheet)
        latest_count_map = calculate_date_counts(latest_records)
        if selected_date and latest_count_map.get(selected_date, 0) >= MAX_CAPACITY_PER_DATE:
            errors.append("Seçtiğiniz tarih dolmuştur. Lütfen farklı bir tarih seçiniz.")

        if errors:
            for message in errors:
                st.error(message)
        else:
            is_custom_topic = topic == OTHER_OPTION_LABEL
            final_topic = custom_topic if is_custom_topic else topic
            timestamp = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")

            row = [
                timestamp,
                student_name,
                category_key,
                CATEGORY_LABELS[category_key],
                topic,
                custom_topic if is_custom_topic else "",
                final_topic,
                selected_date,
                ACTIVE_DATE_LABELS[selected_date],
                "Evet" if is_custom_topic else "Hayır",
            ]

            worksheet.append_row(row, value_input_option="RAW")

            if is_custom_topic:
                st.success(
                    "Kaydınız alındı. Özel başlığınız ders hocasının onayından sonra kesinleşecektir."
                )
            else:
                st.success("Kaydınız başarıyla alındı.")

            st.rerun()

    st.subheader("Tarih Doluluk Durumu")
    st.caption(f"Her aktif tarih için maksimum {MAX_CAPACITY_PER_DATE} kişi seçebilir.")
    availability_table = format_availability_table(count_map)
    st.dataframe(availability_table, use_container_width=True, hide_index=True)

    st.markdown("**Kapalı tarihler**")
    for item in BLOCKED_DATES:
        st.write(f"- {item['label']} ({item['reason']})")

    sheet_id = st.secrets.get("SHEET_ID", "")
    if sheet_id:
        st.markdown(
            f"[Google Sheets kayıt tablosunu aç](https://docs.google.com/spreadsheets/d/{sheet_id})"
        )

    show_admin_panel(records)


if __name__ == "__main__":
    main()
