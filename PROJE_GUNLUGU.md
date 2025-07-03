# Proje Günlüğü

## 30 Haziran 2025

**Dünkü Durum:**
- Optik form tanıma verimliliği üzerine beyin fırtınası yapıldı.
- Form üzerine referans noktaları ekleme, barkod kullanma ve renk değişikliği gibi fikirler tartışıldı.
- `form_uretici.py` dosyasında QR kod oluşturma denemesi yapıldı ancak `python-barcode` kütüphanesinin bunu desteklemediği anlaşıldı.
- Form çizimi sırasında `reportlab` kütüphanesinde `AttributeError: 'Canvas' object has no attribute 'stroke'` hatası alındı.

**Bugünkü Hedefler:**
1.  Proje günlüğünü oluştur ve düzenli olarak güncelle.
2.  `python-barcode` kütüphanesi yerine QR kod üretebilen `qrcode` kütüphanesini projeye dahil et.
3.  `form_uretici.py` dosyasındaki `AttributeError` hatasını düzelt.
4.  Form tasarımını iyileştirmeye başla (renkler, şıkların baloncuk içine yazılması vb.).