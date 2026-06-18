# AI Agent Guidelines (AGENT.md)

Dokumen ini berisi aturan dasar dan instruksi penting yang **wajib dibaca dan diikuti** oleh setiap AI Agent (termasuk Antigravity dan model AI lainnya) saat bekerja pada repositori ini.

---

## 1. Deskripsi Umum Proyek

- Proyek ini adalah sebuah **Frappe App** bernama `akgp_extensions` yang berfungsi sebagai ekstensi kustom untuk ERPNext guna menerapkan workflow spesifik dari Akgp.
- Seluruh pengembangan harus mematuhi standar, arsitektur, dan konvensi penamaan yang ada di dokumentasi resmi **Frappe Framework**.

## 2. Versi Framework & Library

- Untuk paket awal (initial package) atau pustaka (library) baru, **selalu gunakan versi terbaru**.
- Untuk Frappe Framework dan ERPNext, saat ini menggunakan **VERSION-16** (`version-16`).
- Pastikan kode Python dan JavaScript kompatibel dengan standar dan fitur terbaru dari Frappe v16.

## 3. Dependensi & Referensi Kode

- Aplikasi ini bergantung pada aplikasi Frappe yang sudah ada: **erpnext** dan **hrms**.
- AI Agent diperbolehkan dan sangat disarankan untuk memeriksa folder aplikasi tersebut sebagai referensi struktur, pola, dan API:
  - Referensi ERPNext: `../erpnext` (relatif dari root folder `akgp_extensions`)
  - Referensi HRMS: `../hrms` (relatif dari root folder `akgp_extensions`)
  - Jalur Absolut:
    - ERPNext: `/home/arrosa/projects/frappe/Akgp-erp/apps/erpnext`
    - HRMS: `/home/arrosa/projects/frappe/Akgp-erp/apps/hrms`

## 4. Pencarian Dokumentasi & Pustaka

- Jika memerlukan informasi tentang API pihak ketiga, dokumentasi package, atau library, gunakan **`context7` MCP server** (`query-docs` / `resolve-library-id`) untuk membaca dokumentasi yang akurat dan up-to-date.

## 5. Lokasi Folder & Prosedur Migrasi/Uji Coba

- **Root Folder Proyek ini (App)**: `/home/arrosa/projects/frappe/Akgp-erp/apps/akgp_extensions`
- **Root Folder Bench (Frappe Bench)**: `/home/arrosa/projects/frappe/Akgp-erp`
- **Prosedur Setelah Melakukan Update**:
  Setiap kali melakukan perubahan kode (terutama perubahan skema database/DocType, fixtures, atau konfigurasi), **wajib** melakukan update pada site `Akgp.localhost` agar perubahan tersebut diterapkan dan siap dites.

  Jalankan perintah berikut di folder root bench (`/home/arrosa/projects/frappe/Akgp-erp`):

  ```bash
  # Migrasi database dan update skema DocType ke site
  bench --site Akgp.localhost migrate

  # Opsional: Bersihkan cache jika ada perubahan UI/JS/Python caching
  bench --site Akgp.localhost clear-cache
  ```

---

_Catatan untuk AI Agent: Selalu periksa file ini sebelum merencanakan perubahan besar._
