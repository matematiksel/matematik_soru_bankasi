# Proje Günlüğü

## 3 Temmuz 2025

**Strateji Güncellemesi:**
*   Proje verimliliğini ve hızını en üst düzeye çıkarmak için yeni bir çalışma stratejisi benimsenmiştir.
*   Etkileşim sayısını azaltmak amacıyla, görevler daha büyük hedefler olarak tanımlanacak.
*   Gemini, en doğru ve verimli çözüm olduğuna inandığı kararları onay beklemeden alarak otonom bir şekilde ilerleyecektir. Bu, günlük kota limitlerinin en verimli şekilde kullanılmasını sağlayacaktır.

**Yapılanlar:**
*   Projeye Git versiyon kontrolü ve GitHub entegrasyonu başarıyla eklendi.
*   Artık tüm kod değişiklikleri GitHub üzerinden takip edilecek ve yedeklenecek. Bu, projenin teknik "seyir defteri" olarak hizmet görecek.

**Sıradaki Adımlar:**
*   `form_uretici.py` dosyasındaki `AttributeError` hatasını çözmeye devam et.


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