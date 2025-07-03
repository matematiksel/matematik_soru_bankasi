import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Kendi yazdığımız araçları import ediyoruz
from db_utils import veritabani_motoru_olustur, get_dogru_cevaplar
from kagit_olustur import (
    ogrencileri_listele, 
    konulari_listele, 
    calisma_kagidi_icin_sorulari_getir, 
    latex_calisma_kagidi_olustur,
    latex_cevap_anahtari_olustur
)
from optik_okuyucu import read_form, FORM_SECTIONS

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
                st.success("Form başarıyla okundu! Sonuçlar değerlendiriliyor...")
                
                # --- DEĞERLENDİRME MANTIĞI ---
                results_data = scan_results['data']
                
                # Formdaki derslere karşılık gelen konu ID'lerini bul
                # Bu kısım şimdilik form yapısına göre manuel ayarlanıyor.
                # İleride form ID'sinden otomatik çekilebilir.
                konu_map = {
                    "Turkce": 1, "Matematik": 2, "Fen Bilimleri": 3, 
                    "Sosyal Bilgiler": 4, "Din Kulturu": 5, "Ingilizce": 6
                }
                form_konu_idler = [konu_map[sec['name']] for sec in FORM_SECTIONS if sec['type'] == 'row_based']
                
                # Veritabanından doğru cevapları çek
                dogru_cevaplar_df = get_dogru_cevaplar(db_engine, form_konu_idler)

                st.subheader("Sonuç Karnesi")

                # Öğrenci Numarası ve Kitapçık Türü
                col1, col2 = st.columns(2)
                with col1:
                    ogrenci_no_dict = results_data.get("Ogrenci No", {})
                    ogrenci_no_str = "".join([str(ogrenci_no_dict.get(i, '')) for i in range(1, 11)])
                    st.metric(label="Öğrenci Numarası", value=ogrenci_no_str if ogrenci_no_str else "Okunamadı")
                # with col2:
                #     kitapcik_dict = results_data.get("Kitapcik Turu", {})
                #     kitapcik_str = kitapcik_dict.get(1, "Okunamadı")
                #     st.metric(label="Kitapçık Türü", value=kitapcik_str)

                # Ders bazında sonuçları hesapla ve göster
                karne_ozeti = []
                for section_config in FORM_SECTIONS:
                    section_name = section_config['name']
                    if section_config['type'] == 'row_based':
                        ogrenci_cevaplari = results_data.get(section_name, {})
                        konu_id = konu_map[section_name]
                        konu_dogru_cevaplari = dogru_cevaplar_df[dogru_cevaplar_df['konu_id'] == konu_id]
                        
                        if ogrenci_cevaplari:
                            dogru_sayisi, yanlis_sayisi, bos_sayisi = 0, 0, 0
                            detayli_sonuclar = []

                            for soru_no, ogrenci_cevabi in sorted(ogrenci_cevaplari.items()):
                                # Bu kısım, soru_no'nun veritabanındaki soru_id ile eşleştiğini varsayar.
                                # Gerçek senaryoda bu eşleşme daha karmaşık olabilir.
                                dogru_cevap_seri = konu_dogru_cevaplari[konu_dogru_cevaplari['soru_id'] == soru_no]['dogru_cevap']
                                
                                sonuc = ""
                                dogru_cevap = "N/A"
                                if not dogru_cevap_seri.empty:
                                    dogru_cevap = dogru_cevap_seri.iloc[0]
                                    if ogrenci_cevabi == "BOS":
                                        bos_sayisi += 1
                                        sonuc = "➖"
                                    elif ogrenci_cevabi == dogru_cevap:
                                        dogru_sayisi += 1
                                        sonuc = "✅"
                                    else:
                                        yanlis_sayisi += 1
                                        sonuc = "❌"
                                else:
                                    bos_sayisi += 1 # Eşleşme yoksa boş say
                                    sonuc = "❓"

                                detayli_sonuclar.append({
                                    "Soru": soru_no, 
                                    "Cevabınız": ogrenci_cevabi, 
                                    "Doğru Cevap": dogru_cevap,
                                    "Sonuç": sonuc
                                })
                            
                            toplam_soru = dogru_sayisi + yanlis_sayisi + bos_sayisi
                            basari_yuzdesi = (dogru_sayisi / toplam_soru * 100) if toplam_soru > 0 else 0
                            karne_ozeti.append({
                                "Ders": section_name,
                                "Doğru": dogru_sayisi,
                                "Yanlış": yanlis_sayisi,
                                "Boş": bos_sayisi,
                                "Başarı": f"{basari_yuzdesi:.2f}%"
                            })

                            with st.expander(f"{section_name} Detaylı Sonuçlar"):
                                st.dataframe(pd.DataFrame(detayli_sonuclar), use_container_width=True)

                st.subheader("Genel Karne Özeti")
                st.dataframe(pd.DataFrame(karne_ozeti), use_container_width=True)
            else:
                st.error(f"Form okunurken bir hata oluştu: {scan_results['message']}")
            
            # Geçici dosyayı sil
            os.remove("temp_uploaded_form.png")
