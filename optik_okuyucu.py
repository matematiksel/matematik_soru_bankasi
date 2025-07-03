# optik_okuyucu.py
# YENİ VERSİYON: Otomatik Bölüm Tespiti

import cv2
import numpy as np
import os
import traceback

# --- AYARLAR VE SABİTLER ---
TARGET_WIDTH_PX = 700
FORM_WIDTH = 700
FORM_HEIGHT = int(29.7 / 21.0 * FORM_WIDTH) # A4 aspect ratio

# --- YARDIMCI FONKSİYONLAR ---
def reorder_points(points):
    """Verilen 4 noktanın sırasını sol-üst, sağ-üst, sağ-alt, sol-alt olarak düzenler."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]
    rect[2] = points[np.argmax(s)]
    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]
    return rect

def warp_perspective(img, quad):
    """Görüntüyü, bulunan dörtgenin köşelerine göre perspektif olarak düzeltir."""
    rect = reorder_points(quad)
    (tl, tr, br, bl) = rect
    dst = np.array([
        [0, 0],
        [FORM_WIDTH - 1, 0],
        [FORM_WIDTH - 1, FORM_HEIGHT - 1],
        [0, FORM_HEIGHT - 1]], dtype="float32")
    src_points = np.array([tl, tr, br, bl], dtype="float32")
    matrix = cv2.getPerspectiveTransform(src_points, dst)
    return cv2.warpPerspective(img, matrix, (FORM_WIDTH, FORM_HEIGHT))

def preprocess_image(img_path):
    """Görüntüyü okur ve standart bir genişliğe yeniden boyutlandırır."""
    if not os.path.exists(img_path): raise FileNotFoundError(f"Dosya bulunamadı: {img_path}")
    img = cv2.imread(img_path)
    if img is None: raise ValueError("Görüntü okunamadı! Geçersiz format olabilir.")
    scale = TARGET_WIDTH_PX / img.shape[1]
    return cv2.resize(img, (TARGET_WIDTH_PX, int(img.shape[0] * scale)))

# YENİ FONKSİYON: BÖLÜM KUTULARINI OTOMATİK BULMA
def find_section_boxes(img):
    """
    Görüntü üzerindeki ana bölüm dikdörtgenlerini (kontur tespiti ile) bulur.
    """
    # 1. Gri tonlama ve bulanıklaştırma
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Eşiklemeden geçirerek kutuları belirginleştirme
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # 3. Konturları bulma (iç içe olanları da alıyoruz)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    detected_boxes = []
    img_area = img.shape[0] * img.shape[1]

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        # Eğer kontur 4 köşeye sahip bir dikdörtgen ise
        if len(approx) == 4:
            (x, y, w, h) = cv2.boundingRect(approx)
            area = cv2.contourArea(cnt)
            
            # Çok küçük veya çok büyük alanları (tüm sayfa gibi) filtrele
            if (img_area * 0.01) < area < (img_area * 0.4):
                # Makul en-boy oranına sahip olanları seç (çok ince veya uzun olmasın)
                aspect_ratio = float(w) / h
                if 0.2 < aspect_ratio < 5.0:
                    detected_boxes.append((x, y, w, h))

    return detected_boxes

# GÜNCELLENMİŞ ANA FONKSİYON
def main():
    try:
        img_path = "test_form.png"
        original = preprocess_image(img_path)
        
        # Şimdilik formun genel çerçevesini sabit kabul ediyoruz.
        # Bu adım da ileride otomatikleştirilebilir.
        tl, br = (28, 28), (672, 965)
        quad = np.array([tl, (br[0], tl[1]), (tl[0], br[1]), br], dtype="float32")
        processed = warp_perspective(original, quad)
        
        print("\n--- BÖLÜM TESPİTİ BAŞLADI ---\n")
        
        # Yeni fonksiyonumuzu kullanarak bölüm kutularını bulalım
        section_boxes = find_section_boxes(processed.copy())
        
        print(f"Toplam {len(section_boxes)} adet potansiyel bölüm kutusu bulundu.")

        # Sonuçları görselleştirelim
        result_img = processed.copy()
        for (x, y, w, h) in section_boxes:
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 3) # Yeşil, kalın çerçeve

        cv2.imshow("Otomatik Tespit Edilen Bolumler", result_img)
        cv2.imwrite("sonuc.png", result_img) # Sonucu dosyaya da kaydedelim
        print("\nSonucu görmek için açılan resim penceresini kontrol edin.")
        print("Ayrıca 'sonuc.png' dosyasına da kaydedildi.")
        print("Çıkmak için herhangi bir tuşa basın veya pencereyi kapatın.")
        cv2.waitKey(0)

    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        traceback.print_exc()
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()