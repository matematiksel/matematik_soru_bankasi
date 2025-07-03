# kagit_olustur.py

import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
import numpy as np

# Kendi yazdığımız veritabanı araçlarını import ediyoruz
from db_utils import veritabani_motoru_olustur

#=============================================================================
# VERİTABANI İLE ETKİLEŞİM FONKSİYONLARI
#=============================================================================

def ogrencileri_listele(engine):
    """Veritabanındaki öğrencileri listeler ve DataFrame olarak döndürür."""
    with engine.connect() as conn:
        return pd.read_sql_query(text("SELECT * FROM ogrenciler ORDER BY ogrenci_id"), conn)

def konulari_listele(engine):
    """Veritabanındaki konuları listeler ve DataFrame olarak döndürür."""
    with engine.connect() as conn:
        return pd.read_sql_query(text("SELECT konu_id, sinif_seviyesi, alt_konu FROM konular ORDER BY konu_id"), conn)

def adaptif_soru_sec(engine, ogrenci_id, konu_id, soru_sayisi):
    """
    Öğrencinin kazanım bazlı performansını analiz ederek,
    ona en uygun zorluk seviyesindeki soruları seçer.
    """
    with engine.connect() as conn:
        try:
            # 1. Öğrencinin seçilen konudaki tüm kazanımlardaki mevcut seviyelerini al
            kazanim_seviyeleri_sql = """
                SELECT okp.meb_kazanim_kodu, okp.mevcut_seviye
                FROM ogrenci_kazanim_yeterlilik okp
                JOIN sorular s ON okp.meb_kazanim_kodu = s.meb_kazanim_kodu
                WHERE okp.ogrenci_id = :oid AND s.konu_id = :kid
            """
            df_seviyeler = pd.read_sql_query(text(kazanim_seviyeleri_sql), conn, params={'oid': ogrenci_id, 'kid': konu_id})

            if df_seviyeler.empty:
                tum_kazanimlar_sql = "SELECT DISTINCT meb_kazanim_kodu FROM sorular WHERE konu_id = :kid AND meb_kazanim_kodu IS NOT NULL"
                df_tum_kazanimlar = pd.read_sql_query(text(tum_kazanimlar_sql), conn, params={'kid': konu_id})
                zayif_kazanimlar = df_tum_kazanimlar['meb_kazanim_kodu'].tolist()
                hedef_zorluk_araligi = [1, 2]
                st.info(f"Öğrencinin bu konuda geçmişi bulunamadı. Başlangıç seviyesinde (Zorluk 1-2) sorular seçiliyor.")
            else:
                en_dusuk_seviye = df_seviyeler['mevcut_seviye'].min()
                zayif_kazanimlar = df_seviyeler[df_seviyeler['mevcut_seviye'] <= en_dusuk_seviye + 0.5]['meb_kazanim_kodu'].tolist()
                hedef_zorluk = int(round(en_dusuk_seviye))
                hedef_zorluk_araligi = [max(1, hedef_zorluk -1), hedef_zorluk, min(5, hedef_zorluk + 1)]
                st.info(f"Öğrencinin en zayıf olduğu kazanımlar tespit edildi. Seviye: {en_dusuk_seviye:.2f}. Hedef zorluk: {hedef_zorluk_araligi}")
            
            if not zayif_kazanimlar:
                st.warning("Analiz için yeterli veri yok veya öğrenci tüm kazanımlarda başarılı.")
                return pd.DataFrame()

            onceki_sorular_sql = "SELECT soru_id FROM ogrenci_cevaplari WHERE ogrenci_id = :oid"
            df_onceki_sorular = pd.read_sql_query(text(onceki_sorular_sql), conn, params={'oid': ogrenci_id})
            cozulen_soru_listesi = df_onceki_sorular['soru_id'].tolist() or [0]

            soru_getir_sql = """
                SELECT soru_id FROM sorular
                WHERE meb_kazanim_kodu IN :kazanimlar AND zorluk IN :zorluklar AND soru_id NOT IN :cozulen_idler
                ORDER BY RANDOM() LIMIT :limit
            """
            df_secilen_idler = pd.read_sql_query(text(soru_getir_sql), conn, params={
                'kazanimlar': tuple(zayif_kazanimlar), 'zorluklar': tuple(hedef_zorluk_araligi),
                'cozulen_idler': tuple(cozulen_soru_listesi), 'limit': soru_sayisi
            })
            
            secilen_id_listesi = df_secilen_idler['soru_id'].tolist()
            if not secilen_id_listesi: return pd.DataFrame()
            
            detay_sql = """
                SELECT 
                    s.soru_id, s.soru_metni, s.yerlesim_tipi,
                    sec.secenek_harfi, sec.secenek_metni,
                    coz.cozum_tipi, coz.cozum_metni,
                    CASE WHEN dc.dogru_secenek_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_dogru_cevap
                FROM sorular s
                LEFT JOIN secenekler sec ON s.soru_id = sec.soru_id
                LEFT JOIN cozumler coz ON s.soru_id = coz.soru_id
                LEFT JOIN dogru_cevaplar dc ON sec.secenek_id = dc.dogru_secenek_id
                WHERE s.soru_id IN :secilen_idler
                ORDER BY s.soru_id, sec.secenek_harfi, coz.cozum_id;
            """
            return pd.read_sql_query(text(detay_sql), conn, params={'secilen_idler': tuple(secilen_id_listesi)})
        except Exception as e:
            st.error(f"❌ Adaptif soru seçimi sırasında hata: {e}")
            return None

#=============================================================================
# LATEX DOSYASI OLUŞTURMA FONKSİYONLARI
#=============================================================================

def latex_calisma_kagidi_olustur(sorular_df, ogrenci_adi, dosya_adi, secilen_cozum_tipi):
    """Esnek, çift taraflı (soru ve çözüm) LaTeX dosyası oluşturur."""
    try:
        with open(dosya_adi, 'w', encoding='utf-8') as f:
            f.write(r"\documentclass[12pt,a4paper]{article}" + "\n")
            f.write(r"\usepackage[utf8]{inputenc}" + "\n")
            f.write(r"\usepackage[turkish]{babel}" + "\n")
            f.write(r"\usepackage{enumitem}" + "\n")
            f.write(r"\usepackage{geometry}" + "\n")
            f.write(r"\usepackage{multicol}" + "\n")
            f.write(r"\geometry{a4paper, margin=1in}" + "\n\n")
            f.write(r"\setlist[enumerate,1]{label=\textbf{\arabic*.}}" + "\n")
            f.write(r"\setlist[enumerate,2]{label={\textbf{\Alph*)}}, nolistsep}" + "\n\n")
            f.write(r"\title{\textbf{Kişiye Özel Matematik Çalışma Kağıdı}}" + "\n")
            f.write(r"\author{" + ogrenci_adi.replace('_', ' ') + r"}" + "\n")
            f.write(r"\date{\today}" + "\n\n")
            f.write(r"\begin{document}" + "\n")
            f.write(r"\maketitle" + "\n\n")
            f.write(r"\section*{Sorular}" + "\n")
            mevcut_yerlesim = 'genis'
            soru_gruplari = sorted(list(sorular_df.groupby('soru_id')), key=lambda x: x[0])
            f.write(r"\begin{enumerate}" + "\n")
            for i, (soru_id, grup) in enumerate(soru_gruplari):
                hedeflenen_yerlesim = grup['yerlesim_tipi'].iloc[0]
                if hedeflenen_yerlesim != mevcut_yerlesim:
                    if mevcut_yerlesim == 'sutun': f.write(r"\end{enumerate}" + "\n" + r"\end{multicols}" + "\n" + r"\begin{enumerate}[resume]" + "\n")
                    else: f.write(r"\end{enumerate}" + "\n" + r"\begin{multicols}{2}" + "\n" + r"\begin{enumerate}[resume]" + "\n")
                    mevcut_yerlesim = hedeflenen_yerlesim
                soru_metni = grup['soru_metni'].iloc[0].replace('%', r'\%')
                f.write(r"  \item " + soru_metni + "\n")
                secenekler = grup.drop_duplicates(subset=['secenek_harfi']).dropna(subset=['secenek_harfi'])
                if not secenekler.empty:
                    f.write(r"  \begin{enumerate}" + "\n")
                    for _, row in secenekler.sort_values(by='secenek_harfi').iterrows():
                        f.write(r"    \item " + str(row['secenek_metni']).replace('%', r'\%') + "\n")
                    f.write(r"  \end{enumerate}" + "\n")
                f.write(r"  \vspace{1cm}" + "\n")
            if mevcut_yerlesim == 'sutun': f.write(r"\end{enumerate}" + "\n" + r"\end{multicols}" + "\n")
            else: f.write(r"\end{enumerate}" + "\n")
            f.write(r"\newpage" + "\n")
            f.write(r"\section*{Sorular ve Çözümleri (" + secilen_cozum_tipi.capitalize() + r")}" + "\n")
            f.write(r"\begin{enumerate}" + "\n")
            for soru_id, grup in soru_gruplari:
                soru_metni = grup['soru_metni'].iloc[0].replace('%', r'\%')
                f.write(r"  \item " + soru_metni + "\n")
                secenekler = grup.drop_duplicates(subset=['secenek_harfi']).dropna(subset=['secenek_harfi'])
                if not secenekler.empty:
                    f.write(r"  \begin{enumerate}" + "\n")
                    for _, row in secenekler.sort_values(by='secenek_harfi').iterrows():
                        f.write(r"    \item " + str(row['secenek_metni']).replace('%', r'\%') + "\n")
                    f.write(r"  \end{enumerate}" + "\n")
                f.write(r"  \vspace{5pt}" + "\n")
                f.write(r"  \par\noindent\textbf{Çözüm:}" + "\n")
                f.write(r"  \par\noindent ")
                cozum_satiri = grup[grup['cozum_tipi'] == secilen_cozum_tipi].drop_duplicates(subset=['cozum_metni'])
                if not cozum_satiri.empty and cozum_satiri['cozum_metni'].iloc[0] is not None:
                    cozum_metni = cozum_satiri['cozum_metni'].iloc[0].replace('%', r'\%')
                    f.write(cozum_metni + r"\vspace{1cm}" + "\n\n")
                else:
                    f.write(r"Bu soru için '" + secilen_cozum_tipi + r"' tipinde çözüm bulunamadı." + r"\vspace{1cm}" + "\n\n")
            f.write(r"\end{enumerate}" + "\n")
            f.write(r"\end{document}" + "\n")
        return True
    except Exception as e:
        st.error(f"❌ LaTeX dosyası oluşturulurken bir hata oluştu: {e}")
        return False

#=============================================================================
# STREAMLIT ARAYÜZÜ
#=============================================================================

def main():
    st.set_page_config(page_title="Akıllı Soru Bankası", layout="wide")
    st.title("🎓 Adaptif Matematik Asistanı")

    db_engine = veritabani_motoru_olustur()
    if not db_engine:
        st.error("Veritabanı bağlantısı kurulamadı.")
        return

    st.sidebar.header("📝 Çalışma Kağıdı Ayarları")
    
    df_ogrenciler = ogrencileri_listele(db_engine)
    df_konular = konulari_listele(db_engine)

    if df_ogrenciler.empty or df_konular.empty:
        st.warning("Sistemde yeterli öğrenci veya konu bulunmuyor.")
        return

    ogrenci_secenekleri = {row['ogrenci_id']: f"{row['ad']} {row['soyad']} (Sınıf: {row['sinif']})" for _, row in df_ogrenciler.iterrows()}
    konu_secenekleri = {row['konu_id']: f"{row['sinif_seviyesi']}. Sınıf - {row['alt_konu']}" for _, row in df_konular.iterrows()}

    with st.sidebar.form("calisma_kagidi_formu"):
        st.info("Sistem, öğrencinin zayıf olduğu kazanımlara göre soruları otomatik seçecektir.")
        secilen_ogrenci_id = st.selectbox("Öğrenci Seçin:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
        secilen_konu_id = st.selectbox("Konu Seçin:", options=list(konu_secenekleri.keys()), format_func=lambda x: konu_secenekleri[x])
        soru_sayisi = st.number_input("Kaç Soru Oluşturulsun?", min_value=1, max_value=20, value=5)
        secilen_cozum_tipi = st.selectbox("Çözüm Detay Seviyesi:", options=['kisa', 'orta', 'uzun'], index=1)
        
        submitted = st.form_submit_button("🚀 Çalışma Kağıdı Oluştur")

    if submitted:
        st.header("İşlem Sonucu")
        with st.spinner("Öğrenci performansı analiz ediliyor ve sorular seçiliyor..."):
            sorular_df = adaptif_soru_sec(db_engine, secilen_ogrenci_id, secilen_konu_id, soru_sayisi)

            if sorular_df is not None and not sorular_df.empty:
                st.success(f"{len(sorular_df.groupby('soru_id'))} adet kişiselleştirilmiş soru bulundu.")
                
                # --- DOSYA OLUŞTURMA VE İNDİRME LİNKİ EKLEMESİ ---
                ogrenci_bilgi = df_ogrenciler[df_ogrenciler['ogrenci_id'] == secilen_ogrenci_id]
                ogrenci_tam_adi = f"{ogrenci_bilgi['ad'].iloc[0]}_{ogrenci_bilgi['soyad'].iloc[0]}"
                bugun = datetime.now().strftime("%Y%m%d")
                dosya_adi = f"{ogrenci_tam_adi}_Calisma_Kagidi_{bugun}.tex"
                
                basarili = latex_calisma_kagidi_olustur(sorular_df, ogrenci_tam_adi, dosya_adi, secilen_cozum_tipi)

                if basarili:
                    with open(dosya_adi, "r", encoding="utf-8") as file:
                        st.download_button(
                            label=f"Oluşturulan '{dosya_adi}' dosyasını indir",
                            data=file.read(),
                            file_name=dosya_adi,
                            mime='application/x-tex',
                        )
            else:
                st.warning("Analiz sonucunda bu öğrenci için şu anda uygun yeni soru bulunamadı. Lütfen soru bankasını genişletin veya farklı bir konu seçin.")

if __name__ == "__main__":
    main()