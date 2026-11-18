# Android Health & Performance Doctor 🩺📱 (Română)

🌐 **Language / Limba:** **[🇬🇧 English](README.md)** | **[🇷🇴 Română](README.ro.md)**

### Suită universală de diagnosticare și optimizare prin ADB (USB & Wireless Wi-Fi) pentru orice Telefon Android, Tabletă și Android TV / Google TV

**Android Health Doctor** este o aplicație Web + CLI (fără necesitate de Root) concepută pentru a depista și repara cauzele reale pentru care un telefon Android (**Samsung Galaxy, Google Pixel, Xiaomi, OnePlus, Motorola, Asus, Nothing** etc.) sau un televizor / media box cu **Android TV / Google TV** (**Google TV Streamer, Chromecast cu Google TV, Philips Android TV, Sony Bravia, TCL, Xiaomi TV**) începe să meargă sacadat (*UI Jank / Frame Drops*), să rămână fără memorie RAM/ZRAM sau să afișeze erori **„Application Not Responding” (ANR)**.

---

## 🟢 Varianta Simplă (Fără Python și fără instalare ADB!)

Pentru utilizatorii care **nu au Python sau Android Platform Tools instalate pe PC**:
1. **[📥 Apasă aici pentru a descărca `AndroidHealthDoctor.exe` (Aplicație Portabilă într-un singur fișier)](dist/AndroidHealthDoctor.exe)** (sau din secțiunea **[Releases](../../releases)**).
2. Dă dublu-clic pe **`AndroidHealthDoctor.exe`**.
   - Totul este deja inclus într-un singur fișier `.exe`: motorul Python, interfața grafică Web și utilitarul oficial Google `adb.exe`!
   - Chiar dacă `adb.exe` ar lipsi vreodată, aplicația îl descarcă automat de la Google (~6 MB) la prima pornire.
3. Interfața se va deschide singură în browser la `http://127.0.0.1:8899` (poți comuta limba pe **🇷🇴 RO** din butonul din dreapta-sus).

---

## 🔍 Ce investighează și repară aplicația?

1. **Bazele de Date de Sistem Blocate (`android.process.acore`, `MediaStore`, `Downloads`, `GSF`)**:
   - Când baza de date SQLite de contacte (`com.android.providers.contacts` / `acore`) sau indexul media (`com.android.providers.media.module`) se corupe ori intră în buclă de sincronizare, orice aplicație care accesează contactele, tastatura sau fișierele (WhatsApp, Telefon, Mesaje, Galerie, Chrome) îngheață câteva secunde.
   - Oferă reconstrucția curată a bazelor de date de sistem și recompilarea lor în mod nativ `speed` (contactele din contul Google/Cloud se resincronizează automat).

2. **Analiză Sacadare Ecran (GPU Frame Drops / UI Jank) & Hook-uri Accesibilitate**:
   - Interoghează `dumpsys gfxinfo` pentru a calcula procentul de cadre întârziate (*Janky Frames %*) și timpii de randare (95th / 99th percentile) pentru fiecare aplicație.
   - Detectează automat **Serviciile de Accesibilitate** active (autoclickere, utilitare overlay) care interceptează fiecare atingere pe ecran și cauzează micro-stutter sever la scroll.
   - Detectează automat **Launcher-ul implicit al telefonului** (One UI Home, Pixel Launcher, MIUI/HyperOS Home, Nova etc.), curăță cache-ul de shadere și compilează nativ în mod `speed` Launcher-ul, `SystemUI` și `Android System WebView`.

3. **Reparare Profundă pentru Orice Aplicație Instalată (Fără Pierderea Contului)**:
   - Include un explorator al tuturor aplicațiilor instalate pe telefon.
   - Repară aplicațiile care îngheață prin: oprirea firelor blocate (`am force-stop`), ștergerea exclusivă a memoriei cache (`pm clear --cache-only`, păstrând datele și autentificarea!) și compilarea Ahead-of-Time (`cmd package compile -m speed -f`).
   - Permite restricționarea rulării în fundal (`Standby Bucket: restricted` + `RUN_ANY_IN_BACKGROUND ignore`) pentru aplicațiile care consumă baterie și RAM în mod parazit.

4. **Presiunea pe Memoria RAM, ZRAM Swap & Kernel PSI**:
   - Monitorizează gradul de ocupare ZRAM și indicatorii *Pressure Stall Information* (`/proc/pressure/{cpu,memory,io}`).
   - Oprește serviciile parazite din fundal (servicii AI locale neutilizate, telemetrie, jurnale de debugging excesive) și activează *Android Cached App Freezer*.

5. **Conectare Dublă: Cablu USB sau Wireless ADB (100% fără cablu)**:
   - Ideal și pentru telefoanele cu portul USB uzat sau defect: include **auto-detecție mDNS** (`adb mdns services`), asociere cu cod din 6 cifre (`adb pair`) și conectare directă prin Wi-Fi (`adb connect`).
   - Comutator rapid de limbă **🇬🇧 EN / 🇷🇴 RO** direct în interfața web.

---

## 🛠️ Rularea din Codul Sursă Python (Opțional, pentru Dezvoltatori)

1. Instalare dependențe:
   ```bash
   pip install -r requirements.txt
   ```
2. Pornire Interfață Web:
   ```bash
   python main.py
   ```
3. Generare fișier `.exe` portabil:
   Rulează `build_exe.bat` sau `python build_exe.py` pentru a genera `dist/AndroidHealthDoctor.exe`.

---

## 📱 Cum activezi Depanarea USB / Wireless pe telefon?
1. Deschide **Setări** &rarr; **Despre telefon** (*About phone*).
2. Apasă rapid de **7 ori** pe **Număr versiune** (*Build number*) până apare mesajul *„Acum ești un dezvoltator!”*.
3. Mergi în **Setări** &rarr; **Sistem / Setări suplimentare** &rarr; **Opțiuni pentru dezvoltatori**:
   - **Pentru USB**: Activează **Depanare USB** (*USB debugging*).
   - **Pentru Wi-Fi (fără cablu)**: Activează **Depanare wireless** (*Wireless debugging*) și folosește panoul **📶 Wireless ADB** din aplicație.
