# db_utils.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# .env dosyasındaki değişkenleri yükle
load_dotenv()

def veritabani_motoru_olustur():
    """SQLAlchemy motoru (engine) oluşturur."""
    try:
        db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        engine = create_engine(db_uri)
        engine.connect().close()
        return engine
    except Exception as e:
        print(f"❌ Veritabanı motoru oluşturulurken hata: {e}")
        return None

import pandas as pd

def get_dogru_cevaplar(engine, konu_idler):
    """Verilen konu ID'lerine ait tüm soruların doğru cevaplarını getirir."""
    sql = """
        SELECT s.soru_id, s.konu_id, dc.secenek_harfi AS dogru_cevap
        FROM sorular s
        JOIN (
            SELECT dc.soru_id, s.secenek_harfi
            FROM dogru_cevaplar dc
            JOIN secenekler s ON dc.dogru_secenek_id = s.secenek_id
        ) AS dc ON s.soru_id = dc.soru_id
        WHERE s.konu_id IN :konu_idler;
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params={'konu_idler': tuple(konu_idler)})
    return df

def yeni_soru_ekle(engine, **kwargs):
    """
    Veritabanına yeni bir soru ve tüm detaylarını (seçenekler, çözümler, önem derecesi vb.)
    tek bir işlem (transaction) içinde ekler.
    """
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Ana soruyu 'sorular' tablosuna ekle ve yeni eklenen sorunun id'sini al
            sql_soru_ekle = """
                INSERT INTO sorular (
                    soru_kodu, konu_id, zorluk, soru_metni, soru_tipi, 
                    kalite_manuel, meb_kazanim_kodu, satir_tahmini, yerlesim_tipi, onem_derecesi
                )
                VALUES (
                    :soru_kodu, :konu_id, :zorluk, :soru_metni, :soru_tipi, 
                    :kalite_manuel, :meb_kazanim_kodu, :satir_tahmini, :yerlesim_tipi, :onem_derecesi
                ) RETURNING soru_id;
            """
            result = conn.execute(text(sql_soru_ekle), kwargs)
            yeni_soru_id = result.scalar_one()

            # 2. Seçenekleri 'secenekler' tablosuna ekle
            dogru_secenek_id = None
            if kwargs.get('secenekler_dict'):
                for harf, metin in kwargs['secenekler_dict'].items():
                    res_sec = conn.execute(text("INSERT INTO secenekler (soru_id, secenek_harfi, secenek_metni) VALUES (:sid, :sh, :sm) RETURNING secenek_id"), 
                                            {'sid': yeni_soru_id, 'sh': harf, 'sm': metin})
                    secenek_id = res_sec.scalar_one()
                    if harf == kwargs.get('dogru_cevap_harfi'):
                        dogru_secenek_id = secenek_id
            
            # 3. Doğru cevabı 'dogru_cevaplar' tablosuna işle
            if dogru_secenek_id:
                conn.execute(text("INSERT INTO dogru_cevaplar (soru_id, dogru_secenek_id) VALUES (:sid, :dsid)"), 
                             {'sid': yeni_soru_id, 'dsid': dogru_secenek_id})

            # 4. Çoklu çözümleri 'cozumler' tablosuna ekle
            if kwargs.get('cozumler_dict'):
                for cozum_tipi, cozum_metni in kwargs['cozumler_dict'].items():
                    conn.execute(text("INSERT INTO cozumler (soru_id, cozum_tipi, cozum_metni) VALUES (:sid, :ct, :cm)"),
                                 {'sid': yeni_soru_id, 'ct': cozum_tipi, 'cm': cozum_metni})
            
            # 5. Tüm işlemler başarılı olduysa, veritabanındaki değişiklikleri onayla
            trans.commit()
            print(f"✅ Soru '{kwargs['soru_kodu']}' başarıyla eklendi.")
            return yeni_soru_id

        except Exception as e:
            # Herhangi bir adımda hata olursa, o ana kadar yapılan tüm değişiklikleri geri al
            print(f"❌ HATA: Soru '{kwargs.get('soru_kodu')}' eklenirken: {e}")
            trans.rollback()
            return None
