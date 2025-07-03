import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Kendi yazdığımız araçları import ediyoruz
from db_utils import veritabani_motoru_olustur
from kagit_olustur import (
    ogrencileri_listele, 
    konulari_listele, 
    calisma_kagidi_icin_sorulari_getir, 
    latex_calisma_kagidi_olustur,
    latex_cevap_anahtari_olustur
)
from optik_okuyucu import read_form

st.set_page_config(page_title="Akıllı Soru Bankası", layout="wide")

# --- ANA BAŞLIK ---
st.title("👨‍🏫 Akıllı Matematik Soru Bankası")

# --- VERİTABANI BAĞLANTISI ---
db_engine = veritabani_motoru_olustur()
if not db_engine:
    st.error("Veritabanı bağlantısı kurulamadı. Lütfen .env dosyanızı ve veritabanı sunucunuzun durumunu kontrol edin.")
    st.stop()

# --- SEKME YAPISI ---
tab1, tab2 = st.tabs(["📝 Çalışma Kağıdı Oluştur", "🧐 Optik Form Oku"])

# --- SEKME 1: ÇALIŞMA KAĞIDI OLUŞTURMA ---
with tab1:
    st.header("Çalışma Kağıdı Oluşturma Formu")

    df_ogrenciler = ogrencileri_listele(db_engine)
    df_konular = konulari_listele(db_engine)
    
    ogrenci_secenekleri = {row['ogrenci_id']: f"{row['ad']} {row['soyad']} (Sınıf: {row['sinif']})" for index, row in df_ogrenciler.iterrows()}
    konu_secenekleri = {row['konu_id']: f"{row['sinif_seviyesi']}. Sınıf - {row['alt_konu']}" for index, row in df_konular.iterrows()}

    with st.form("calisma_kagidi_formu"):
        st.subheader("Lütfen Kriterleri Belirleyin")
        
        secilen_ogrenci_id = st.selectbox("Öğrenci Seçin:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
        secilen_konu_id = st.selectbox("Konu Seçin:", options=list(konu_secenekleri.keys()), format_func=lambda x: konu_secenekleri[x])
        
        col1, col2 = st.columns(2)
        with col1:
            zorluk = st.slider("Zorluk Seviyesi:", min_value=1, max_value=5, value=3)
            soru_sayisi = st.number_input("Soru Sayısı:", min_value=1, max_value=20, value=5)
        with col2:
            cikti_tipi = st.radio("Çıktı Tipi:", options=['Çalışma Kağıdı', 'Cevap Anahtarı'])
            secilen_cozum_tipi = st.selectbox("Çözüm Detay Seviyesi:", options=['kisa', 'orta', 'uzun'])

        submitted_kagıt = st.form_submit_button("Çalışma Kağıdını Oluştur")

    if submitted_kagıt:
        with st.spinner("İsteğiniz işleniyor, lütfen bekleyin..."):
            ogrenci_adi = df_ogrenciler[df_ogrenciler['ogrenci_id'] == secilen_ogrenci_id]['ad'].iloc[0]
            ogrenci_soyadi = df_ogrenciler[df_ogrenciler['ogrenci_id'] == secilen_ogrenci_id]['soyad'].iloc[0]
            ogrenci_tam_adi = f"{ogrenci_adi}_{ogrenci_soyadi}"
            
            sorular_df = calisma_kagidi_icin_sorulari_getir(db_engine, secilen_ogrenci_id, secilen_konu_id, zorluk, soru_sayisi, 9999)

            if sorular_df is not None and not sorular_df.empty:
                st.success(f"{len(sorular_df.groupby('soru_id'))} adet uygun soru bulundu ve dosya oluşturuluyor.")
                bugun = datetime.now().strftime("%Y%m%d")

                if cikti_tipi == 'Çalışma Kağıdı':
                    dosya_adi = f"{ogrenci_tam_adi}_Calisma_Kagidi_{bugun}.tex"
                    latex_calisma_kagidi_olustur(sorular_df, ogrenci_tam_adi, dosya_adi, secilen_cozum_tipi)
                else:
                    dosya_adi = f"{ogrenci_tam_adi}_Cevap_Anahtari_{bugun}.tex"
                    latex_cevap_anahtari_olustur(sorular_df, ogrenci_tam_adi, dosya_adi)
                
                with open(dosya_adi, "r", encoding="utf-8") as file:
                    st.download_button(
                        label=f"Oluşturulan '{dosya_adi}' dosyasını indir",
                        data=file.read(),
                        file_name=dosya_adi,
                        mime='application/x-tex',
                    )
            else:
                st.warning("Belirtilen kriterlere uygun yeni soru bulunamadı.")

# --- SEKME 2: OPTİK FORM OKUMA ---
with tab2:
    st.header("Optik Form Okuma Aracı")
    st.info("Lütfen doldurduğunuz optik formun taranmış veya çekilmiş fotoğrafını (.jpg, .png) yükleyin.")

    uploaded_file = st.file_uploader("Optik Formu Yükleyin", type=["jpg", "png"])

    if uploaded_file is not None:
        # Dosyayı geçici bir konuma kaydet
        with open(os.path.join("temp_uploaded_form.png"), "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.image(uploaded_file, caption="Yüklenen Form", width=300)

        with st.spinner("Form okunuyor ve analiz ediliyor..."):
            scan_results = read_form("temp_uploaded_form.png", debug=False)

            if scan_results["status"] == "success":
                st.success("Form başarıyla okundu!")
                st.subheader("Okunan Cevaplar")

                # Sonuçları daha okunaklı hale getir
                results_data = scan_results['data']
                
                # Öğrenci Numarası ve Kitapçık Türü
                ogrenci_no_dict = results_data.get("Ogrenci No", {})
                ogrenci_no_str = "".join([str(ogrenci_no_dict.get(i, '')) for i in range(1, 11)])
                st.metric(label="Öğrenci Numarası", value=ogrenci_no_str if ogrenci_no_str else "Okunamadı")

                # Ders Cevapları
                for section_name, answers in results_data.items():
                    if section_name not in ["Ogrenci No", "Kitapcik Turu"]:
                        with st.expander(f"{section_name} Cevapları"):
                            # Cevapları 2 sütunlu bir DataFrame'e dönüştür
                            answer_items = sorted(answers.items())
                            df = pd.DataFrame(answer_items, columns=["Soru", "Cevap"])
                            st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Form okunurken bir hata oluştu: {scan_results['message']}")
            
            # Geçici dosyayı sil
            os.remove("temp_uploaded_form.png")
