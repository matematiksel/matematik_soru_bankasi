# app.py (Streamlit Arayüzü)

import streamlit as st
import pandas as pd
from datetime import datetime

# Kendi yazdığımız araçları import ediyoruz
from db_utils import veritabani_motoru_olustur
from kagit_olustur import (
    ogrencileri_listele, 
    konulari_listele, 
    calisma_kagidi_icin_sorulari_getir, 
    latex_calisma_kagidi_olustur,
    latex_cevap_anahtari_olustur
)

st.set_page_config(page_title="Akıllı Soru Bankası", layout="wide")
st.title("👨‍🏫 Akıllı Matematik Soru Bankası")

db_engine = veritabani_motoru_olustur()

if not db_engine:
    st.error("Veritabanı bağlantısı kurulamadı. Lütfen .env dosyanızı ve veritabanı sunucunuzun durumunu kontrol edin.")
else:
    # --- KULLANICI GİRİŞ FORMU ---
    st.header("Çalışma Kağıdı Oluşturma Formu")

    df_ogrenciler = ogrencileri_listele(db_engine)
    df_konular = konulari_listele(db_engine)
    
    # Öğrenci ve konu listelerini daha okunabilir hale getirelim
    ogrenci_secenekleri = {row['ogrenci_id']: f"{row['ad']} {row['soyad']} (Sınıf: {row['sinif']})" for index, row in df_ogrenciler.iterrows()}
    konu_secenekleri = {row['konu_id']: f"{row['sinif_seviyesi']}. Sınıf - {row['alt_konu']}" for index, row in df_konular.iterrows()}

    # Form oluşturarak tüm seçimlerin tek bir butona bağlanmasını sağlıyoruz
    with st.form("calisma_kagidi_formu"):
        st.subheader("Lütfen Kriterleri Belirleyin")
        
        # Seçim kutuları
        secilen_ogrenci_id = st.selectbox("Öğrenci Seçin:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
        secilen_konu_id = st.selectbox("Konu Seçin:", options=list(konu_secenekleri.keys()), format_func=lambda x: konu_secenekleri[x])
        
        # Sayı giriş alanları ve diğer seçenekler
        col1, col2 = st.columns(2)
        with col1:
            zorluk = st.slider("Zorluk Seviyesi:", min_value=1, max_value=5, value=3)
            soru_sayisi = st.number_input("Soru Sayısı:", min_value=1, max_value=20, value=5)
        with col2:
            cikti_tipi = st.radio("Çıktı Tipi:", options=['Çalışma Kağıdı', 'Cevap Anahtarı'])
            secilen_cozum_tipi = st.selectbox("Çözüm Detay Seviyesi:", options=['kisa', 'orta', 'uzun'])

        # Formu gönderme butonu
        submitted = st.form_submit_button("Çalışma Kağıdını Oluştur")

    # --- İŞLEM KISMI ---
    if submitted:
        with st.spinner("İsteğiniz işleniyor, lütfen bekleyin..."):
            ogrenci_adi = df_ogrenciler[df_ogrenciler['ogrenci_id'] == secilen_ogrenci_id]['ad'].iloc[0]
            ogrenci_soyadi = df_ogrenciler[df_ogrenciler['ogrenci_id'] == secilen_ogrenci_id]['soyad'].iloc[0]
            ogrenci_tam_adi = f"{ogrenci_adi}_{ogrenci_soyadi}"
            
            # Soruları veritabanından çek
            sorular_df = calisma_kagidi_icin_sorulari_getir(db_engine, secilen_ogrenci_id, secilen_konu_id, zorluk, soru_sayisi, 9999)

            if sorular_df is not None and not sorular_df.empty:
                st.success(f"{len(sorular_df.groupby('soru_id'))} adet uygun soru bulundu ve dosya oluşturuluyor.")
                bugun = datetime.now().strftime("%Y%m%d")

                if cikti_tipi == 'Çalışma Kağıdı':
                    dosya_adi = f"{ogrenci_tam_adi}_Calisma_Kagidi_{bugun}.tex"
                    latex_calisma_kagidi_olustur(sorular_df, ogrenci_tam_adi, dosya_adi, secilen_cozum_tipi)
                else: # Cevap Anahtarı
                    dosya_adi = f"{ogrenci_tam_adi}_Cevap_Anahtari_{bugun}.tex"
                    latex_cevap_anahtari_olustur(sorular_df, ogrenci_tam_adi, dosya_adi)
                
                # Oluşturulan dosyayı indirme linki olarak sun
                with open(dosya_adi, "r", encoding="utf-8") as file:
                    st.download_button(
                        label=f"Oluşturulan '{dosya_adi}' dosyasını indir",
                        data=file.read(),
                        file_name=dosya_adi,
                        mime='application/x-tex',
                    )
            else:
                st.warning("Belirtilen kriterlere uygun yeni soru bulunamadı.")