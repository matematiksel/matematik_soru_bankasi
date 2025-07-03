# form_uretici.py
# V16.0 Mimarisi: Kitapçık türü aralığı düzeltilmiş, üretime hazır nihai sürüm
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
import qrcode

# --- FORM YAPILANDIRMASI ---
FORM_ID = "6Ders_20Soru_4Sik_V16"
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

# --- TASARIM AYARLARI ---
DROPOUT_COLOR = colors.HexColor('#2A629C') # Profesyonel Mavi
PRIMARY_COLOR = colors.black
SHADING_COLOR = colors.HexColor('#F0F0F0')   # Açık Gri (Zebra için)
PAGE_WIDTH, PAGE_HEIGHT = A4
BUBBLE_RADIUS = 0.18 * cm # Okunabilirlik için biraz büyütüldü

# --- YARDIMCI ÇİZİM FONKSİYONLARI ---
def draw_main_fiducials(c, margin=0.5*cm):
    c.setFillColor(PRIMARY_COLOR)
    size = 0.4 * cm
    c.rect(margin, PAGE_HEIGHT - margin - size, size, size, fill=1)
    c.rect(PAGE_WIDTH - margin - size, PAGE_HEIGHT - margin - size, size, size, fill=1)
    c.rect(margin, margin, size, size, fill=1)
    c.rect(PAGE_WIDTH - margin - size, margin, size, size, fill=1)

def draw_comprehensive_fiducials(c, start_y, end_y, x_pos=0.5*cm, spacing=0.45*cm):
    """Sayfanın tamamı için bir GPS ağı gibi çalışan kapsamlı referans çizgileri çizer."""
    c.setFillColor(PRIMARY_COLOR)
    bar_height = 0.05 * cm
    bar_width = 0.5 * cm
    num_bars = int((start_y - end_y) / spacing)
    for i in range(num_bars):
        y = start_y - i * spacing
        c.rect(x_pos, y - bar_height/2, bar_width, bar_height, fill=1, stroke=0)

def draw_barcode(c, form_id, x, y):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=8, border=2)
    qr.add_data(form_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    barcode_path = f'{form_id}_qrcode.png'
    img.save(barcode_path)
    c.drawImage(barcode_path, x, y, width=2.5*cm, height=2.5*cm)
    os.remove(barcode_path)

def draw_section(c, section, start_x, start_y):
    name = section['name']
    rows = section['rows']
    cols = section['cols']
    labels = section.get('labels', [chr(ord('A') + i) for i in range(cols)])

    bubble_y_spacing = 0.45 * cm
    bubble_x_spacing = 0.5 * cm
    frame_start_x = start_x - 0.7*cm
    content_end_x = start_x + (cols - 1) * bubble_x_spacing + 0.2*cm + BUBBLE_RADIUS
    frame_width = (content_end_x - frame_start_x) + 0.3*cm

    c.setStrokeColor(DROPOUT_COLOR)
    c.setLineWidth(0.5)
    section_height = (rows + 1.5) * bubble_y_spacing
    c.rect(frame_start_x, start_y - section_height + 0.2*cm, frame_width, section_height, stroke=1, fill=0)

    title_center_x = frame_start_x + frame_width / 2
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(DROPOUT_COLOR)
    c.drawCentredString(title_center_x, start_y, name)

    c.setFont("Helvetica", 7)
    for r in range(rows):
        y = start_y - (r + 1.2) * bubble_y_spacing
        bubble_center_y = y + 0.05*cm
        
        if r % 2 == 1:
            c.setFillColor(SHADING_COLOR)
            c.rect(frame_start_x + 0.1*cm, bubble_center_y - bubble_y_spacing/2, frame_width - 0.2*cm, bubble_y_spacing, fill=1, stroke=0)

        c.setFillColor(DROPOUT_COLOR)
        c.drawCentredString(start_x - 0.2*cm, bubble_center_y - 0.06*cm, str(r + 1))

        for col in range(cols):
            x = start_x + col * bubble_x_spacing
            c.setStrokeColor(DROPOUT_COLOR)
            c.circle(x + 0.2*cm, bubble_center_y, BUBBLE_RADIUS, stroke=1, fill=0)
            c.setFillColor(DROPOUT_COLOR)
            c.drawCentredString(x + 0.2*cm, bubble_center_y - 0.06*cm, labels[col])

def draw_personal_info_section(c, section, start_x, start_y):
    name = section['name']
    rows = section['rows']
    cols = section['cols']
    
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(DROPOUT_COLOR)
    c.drawString(start_x, start_y, name)

    c.setFont("Helvetica", 7)
    y_spacing = 0.45 * cm
    x_spacing = 0.45 * cm
    for r in range(rows):
        y = start_y - (r + 1.2) * y_spacing
        for col in range(cols):
            x = start_x + col * x_spacing
            c.setStrokeColor(DROPOUT_COLOR)
            c.circle(x, y, BUBBLE_RADIUS, stroke=1, fill=0)
            c.setFillColor(DROPOUT_COLOR)
            c.drawCentredString(x, y - 0.06*cm, str(r))

# --- ANA FONKSİYON ---
def create_form():
    pdf_path = f"{FORM_ID}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)

    draw_main_fiducials(c)
    
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(PRIMARY_COLOR)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 1.5*cm, "Akilli Optik Form V16.0")
    draw_barcode(c, FORM_ID, PAGE_WIDTH - 4*cm, PAGE_HEIGHT - 4*cm)

    draw_personal_info_section(c, FORM_SECTIONS[0], 2.5*cm, PAGE_HEIGHT - 3*cm)
    
    kitapcik_sec = FORM_SECTIONS[1]
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(DROPOUT_COLOR)
    c.drawString(10*cm, PAGE_HEIGHT - 3*cm, kitapcik_sec['name'])
    kitapcik_y = PAGE_HEIGHT - 3.5*cm
    for i, label in enumerate(kitapcik_sec['labels']):
        x = 10*cm + i * 0.8*cm # Daireler arası boşluk azaltıldı
        c.circle(x + 0.5*cm, kitapcik_y, BUBBLE_RADIUS, stroke=1, fill=0)
        c.drawCentredString(x + 0.5*cm, kitapcik_y - 0.08*cm, label)

    ders_sections = FORM_SECTIONS[2:]
    num_cols = len(ders_sections)
    col_width = (PAGE_WIDTH - 3.5*cm) / num_cols
    start_y_dersler = PAGE_HEIGHT - 9*cm
    
    for i, section in enumerate(ders_sections):
        start_x = 2.5*cm + i * col_width
        draw_section(c, section, start_x, start_y_dersler)

    # Kapsamlı Referans Ağı (Tüm dikey alanı kapsar)
    draw_comprehensive_fiducials(c, PAGE_HEIGHT - 2.5*cm, 2*cm)

    c.save()
    print(f"Basarili! '{pdf_path}' dosyasi olusturuldu.")

if __name__ == "__main__":
    create_form()
