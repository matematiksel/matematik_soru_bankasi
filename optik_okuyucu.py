# optik_okuyucu.py
# V2.0: Isaretlenmis cevaplari okuma ve yapilandirilmis veri dondurme

import cv2
import numpy as np
import os
import traceback
from reportlab.lib.units import cm

# --- FORM YAPILANDIRMASI (form_uretici.py'den kopyalandi) ---
# Bu yapinin, okunan form ile uyumlu oldugundan emin olunmalidir.
FORM_SECTIONS = [
    {"name": "Ogrenci No", "type": "column_based", "rows": 10, "cols": 10},
    {"name": "Kitapcik Turu", "type": "column_based", "rows": 4, "cols": 1, "labels": ["A", "B", "C", "D"]},
    {"name": "Turkce", "type": "row_based", "rows": 20, "cols": 4},
    {"name": "Matematik", "type": "row_based", "rows": 20, "cols": 4},
    {"name": "Fen Bilimleri", "type": "row_based", "rows": 20, "cols": 4},
    {"name": "Sosyal Bilgiler", "type": "row_based", "rows": 20, "cols": 4},
    {"name": "Din Kulturu", "type": "row_based", "rows": 20, "cols": 4},
    {"name": "Ingilizce", "type": "row_based", "rows": 20, "cols": 4},
]
BUBBLE_RADIUS_CM = 0.18
BUBBLE_Y_SPACING_CM = 0.45
BUBBLE_X_SPACING_CM = 0.5

# --- AYARLAR VE SABİTLER ---
TARGET_WIDTH_PX = 800 # Çözünürlük artırıldı
FORM_WIDTH_PX = TARGET_WIDTH_PX
FORM_HEIGHT_PX = int(29.7 / 21.0 * FORM_WIDTH_PX) # A4 aspect ratio
PIXELS_PER_CM = FORM_WIDTH_PX / 21.0 # Yaklaşık cm -> piksel dönüşümü

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
        [FORM_WIDTH_PX - 1, 0],
        [FORM_WIDTH_PX - 1, FORM_HEIGHT_PX - 1],
        [0, FORM_HEIGHT_PX - 1]], dtype="float32")
    src_points = np.array([tl, tr, br, bl], dtype="float32")
    matrix = cv2.getPerspectiveTransform(src_points, dst)
    return cv2.warpPerspective(img, matrix, (FORM_WIDTH_PX, FORM_HEIGHT_PX))

def preprocess_image(img_path):
    """Görüntüyü okur ve standart bir genişliğe yeniden boyutlandırır."""
    if not os.path.exists(img_path): raise FileNotFoundError(f"Dosya bulunamadı: {img_path}")
    img = cv2.imread(img_path)
    if img is None: raise ValueError("Görüntü okunamadı! Geçersiz format olabilir.")
    scale = TARGET_WIDTH_PX / img.shape[1]
    return cv2.resize(img, (TARGET_WIDTH_PX, int(img.shape[0] * scale)))

def find_main_contour(img):
    """Görüntüdeki en büyük dörtgeni (formun kendisi) bulur."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    return None

def process_answers(section_img, section_config):
    """
    Bir bölüm görüntüsünü alır, içindeki işaretli baloncukları bulur ve cevapları döndürür.
    """
    # Görüntüyü işle: gri tonlama ve eşikleme
    gray = cv2.cvtColor(section_img, cv2.COLOR_BGR2GRAY)
    # Eşikleme, dolu baloncukları (siyah) beyaz, boş alanları siyah yapar
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    answers = {}
    rows = section_config['rows']
    cols = section_config['cols']
    labels = section_config.get('labels', [chr(ord('A') + i) for i in range(cols)])

    # Boyutları cm'den piksele çevir
    bubble_y_spacing_px = BUBBLE_Y_SPACING_CM * PIXELS_PER_CM
    bubble_x_spacing_px = BUBBLE_X_SPACING_CM * PIXELS_PER_CM
    bubble_radius_px = BUBBLE_RADIUS_CM * PIXELS_PER_CM

    # Bölüm içindeki göreceli başlangıç noktalarını ayarla
    start_x_offset = 0.9 * cm * PIXELS_PER_CM
    start_y_offset = 1.2 * cm * PIXELS_PER_CM

    for r in range(rows):
        marked_pixels = []
        for c in range(cols):
            # Her bir baloncuğun merkez koordinatını hesapla
            center_x = int(start_x_offset + c * bubble_x_spacing_px)
            center_y = int(start_y_offset + r * bubble_y_spacing_px)
            
            # Baloncuğun etrafında bir maske oluştur
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.circle(mask, (center_x, center_y), int(bubble_radius_px), 255, -1)
            
            # Maskeyi kullanarak sadece o baloncuğun içindeki pikselleri al
            mask = cv2.bitwise_and(thresh, thresh, mask=mask)
            total = cv2.countNonZero(mask)
            marked_pixels.append(total)

        # En çok siyah piksel içeren baloncuğu bul
        if max(marked_pixels) > (np.pi * bubble_radius_px**2 * 0.3): # %30'dan fazla doluysa işaretli say
            selected_index = np.argmax(marked_pixels)
            answers[r + 1] = labels[selected_index]
        else:
            answers[r + 1] = "BOS"
            
    return answers


def read_form(img_path, debug=False):
    """
    Ana optik okuma fonksiyonu. Bir resim dosyası yolu alır ve
    içindeki işaretlenmiş cevapları yapılandırılmış bir sözlük olarak döndürür.
    """
    try:
        original_img = preprocess_image(img_path)
        
        main_contour = find_main_contour(original_img)
        if main_contour is None:
            raise ValueError("Formun ana hatları tespit edilemedi.")
        
        processed_img = warp_perspective(original_img, main_contour)
        
        results = {}
        
        # --- BÖLÜM KOORDİNATLARINI HESAPLA ---
        # Ogrenci No ve Kitapçık Türü
        ogrenci_no_section = FORM_SECTIONS[0]
        kitapcik_section = FORM_SECTIONS[1]
        
        x1_ogrenci = int(2.5*cm * PIXELS_PER_CM - 0.7*cm * PIXELS_PER_CM)
        y1_ogrenci = int(3*cm * PIXELS_PER_CM - 0.5*cm * PIXELS_PER_CM)
        h_ogrenci = int((ogrenci_no_section['rows'] + 2.5) * BUBBLE_Y_SPACING_CM * PIXELS_PER_CM)
        w_ogrenci = int((ogrenci_no_section['cols'] + 1) * BUBBLE_X_SPACING_CM * PIXELS_PER_CM)
        ogrenci_no_roi = processed_img[y1_ogrenci:y1_ogrenci+h_ogrenci, x1_ogrenci:x1_ogrenci+w_ogrenci]
        results[ogrenci_no_section['name']] = process_answers(ogrenci_no_roi, ogrenci_no_section)

        # Ders Bölümleri
        ders_sections = FORM_SECTIONS[2:]
        num_cols = len(ders_sections)
        col_width_px = (FORM_WIDTH_PX - 3.5*cm * PIXELS_PER_CM) / num_cols
        start_y_dersler = int((29.7 - 9) * cm * PIXELS_PER_CM)

        for i, section in enumerate(ders_sections):
            start_x = int(2.5*cm * PIXELS_PER_CM + i * col_width_px)
            
            # ROI koordinatlarını form_uretici.py'deki mantığa göre hesapla
            frame_start_x = int(start_x - 0.7*cm * PIXELS_PER_CM)
            section_height = int((section['rows'] + 1.5) * BUBBLE_Y_SPACING_CM * PIXELS_PER_CM)
            frame_y = int(start_y_dersler - section_height + 0.2*cm * PIXELS_PER_CM)
            frame_width = int(col_width_px + 0.5*cm*PIXELS_PER_CM)

            ders_roi = processed_img[frame_y:frame_y+section_height, frame_start_x:frame_start_x+frame_width]
            results[section['name']] = process_answers(ders_roi, section)
            
            if debug:
                cv2.rectangle(processed_img, (frame_start_x, frame_y), (frame_start_x + frame_width, frame_y + section_height), (0, 255, 0), 2)

        if debug:
            cv2.imshow("Islemis Form ve Bolumler", processed_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return {"status": "success", "data": results}

    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": f"Beklenmedik bir hata oluştu: {e}"}


if __name__ == "__main__":
    # Test için
    test_image_path = "test_form.png" # Bu dosyanın mevcut oldugundan emin olun
    if not os.path.exists(test_image_path):
        print(f"UYARI: Test dosyasi '{test_image_path}' bulunamadi. Lutfen bir form resmi olusturun.")
    else:
        scan_results = read_form(test_image_path)
        print("\n--- TARAMA SONUÇLARI ---")
        print(scan_results)
