# soru_ekle.py

from db_utils import veritabani_motoru_olustur, yeni_soru_ekle
import re

def satir_tahmini_hesapla(soru_metni, secenekler_dict, cozumler_dict):
    """Karakter ve satır sayısına göre basit bir yer kaplama metriği hesaplar."""
    toplam_karakter = len(soru_metni)
    for metin in secenekler_dict.values():
        toplam_karakter += len(metin)
    
    orta_cozum_metni = cozumler_dict.get('orta', '')
    toplam_karakter += len(orta_cozum_metni)

    tahmin = (toplam_karakter // 75) + len(secenekler_dict) + (len(orta_cozum_metni) // 75) + 4
    return tahmin

def metinden_soru_ayikla(dosya_icerigi):
    """
    Verilen metin içeriğini, belirlediğimiz formata göre parçalara ayırır
    ve bir soru listesi döndürür.
    """
    sorular = []
    soru_bloklari = dosya_icerigi.split('---SORU---')
    
    for blok in soru_bloklari:
        if not blok.strip(): continue
        try:
            soru = {}
            soru['soru_kodu'] = re.search(r"soru_kodu:\s*(.*)", blok).group(1).strip()
            soru['konu_id'] = int(re.search(r"konu_id:\s*(.*)", blok).group(1).strip())
            soru['zorluk'] = int(re.search(r"zorluk:\s*(.*)", blok).group(1).strip())
            soru['soru_tipi'] = 'coktan_secmeli'
            
            # Opsiyonel alanları oku, yoksa varsayılan değer ata
            onem_d = re.search(r"onem_derecesi:\s*(.*)", blok)
            soru['onem_derecesi'] = int(onem_d.group(1).strip()) if onem_d else 2

            kalite_m = re.search(r"kalite_manuel:\s*(.*)", blok)
            soru['kalite_manuel'] = int(kalite_m.group(1).strip()) if kalite_m else None
            
            yerlesim_t = re.search(r"yerlesim_tipi:\s*(.*)", blok)
            soru['yerlesim_tipi'] = yerlesim_t.group(1).strip() if yerlesim_t else 'genis'
            
            kazanim_k = re.search(r"meb_kazanim_kodu:\s*(.*)", blok)
            soru['meb_kazanim_kodu'] = kazanim_k.group(1).strip() if kazanim_k else None

            soru['soru_metni'] = re.search(r"soru_metni:(.*?)---SEÇENEKLER---", blok, re.DOTALL).group(1).strip()
            
            secenekler_metni = re.search(r"---SEÇENEKLER---(.*?)---DOĞRU CEVAP---", blok, re.DOTALL).group(1).strip()
            soru['secenekler_dict'] = {harf.strip(): metin.strip() for harf, metin in (satir.split(':', 1) for satir in secenekler_metni.split('\n') if ':' in satir)}
            
            soru['dogru_cevap_harfi'] = re.search(r"---DOĞRU CEVAP---(.*?)(---ÇÖZÜMLER---|$)", blok, re.DOTALL).group(1).strip()

            cozumler_metni_match = re.search(r"---ÇÖZÜMLER---(.*)", blok, re.DOTALL)
            soru['cozumler_dict'] = {tip.strip(): metin.strip() for tip, metin in (satir.split(':', 1) for satir in cozumler_metni_match.group(1).strip().split('\n') if ':' in satir)} if cozumler_metni_match else {}

            soru['satir_tahmini'] = satir_tahmini_hesapla(soru['soru_metni'], soru['secenekler_dict'], soru['cozumler_dict'])
            
            sorular.append(soru)
        except Exception as e:
            print(f"⚠️ UYARI: Bir soru bloğu okunamadı: {e}. Blok atlanıyor: \n{blok[:100]}...")
            continue
    return sorular

def main():
    """Ana program akışı."""
    db_engine = veritabani_motoru_olustur()
    if not db_engine: 
        return
    
    dosya_adi = input("> Soruları içeren metin dosyasının adını girin (örn: yeni_sorular.txt): ")
    try:
        with open(dosya_adi, 'r', encoding='utf-8') as f: 
            icerik = f.read()
        
        sorular = metinden_soru_ayikla(icerik)
        
        if not sorular:
            print("Dosyada işlenecek soru bulunamadı veya format hatası mevcut.")
            return
            
        print(f"\nDosyada {len(sorular)} adet soru bulundu. Veritabanına ekleniyor...")
        for soru in sorular:
            yeni_soru_ekle(engine=db_engine, **soru)
            
    except FileNotFoundError: 
        print(f"HATA: '{dosya_adi}' adında bir dosya bulunamadı.")
    except Exception as e: 
        print(f"Genel bir hata oluştu: {e}")

if __name__ == "__main__":
    main()

