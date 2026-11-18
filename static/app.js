document.addEventListener('DOMContentLoaded', () => {
  let activeDevice = null;
  let selectedSerial = null;
  let statusPollInterval = null;
  let jobPollInterval = null;
  let currentLang = localStorage.getItem('ahd_lang') || 'en';
  let lastScanReport = null;

  const I18N = {
    en: {
      header_subtitle: 'Deep diagnostics & repair for UI Jank, App Freezes (ANRs), System Databases, Bloatware & ART Compilation (USB / Wi-Fi)',
      btn_remote_header: '🎮 Remote & APK Sideload',
      btn_wireless_header: '📶 Wireless ADB (No USB)',
      btn_guide: 'ADB Setup Guide',
      lbl_active_device: 'Active device:',
      btn_wireless_mode: '📶 Wireless Wi-Fi Mode',
      btn_super_boost_top: '⚡ 1-Click Super Boost',
      btn_scan_phone: 'Scan Device',
      remote_panel_title: '🎮 Virtual Remote Control, PC Keyboard & APK Sideloader',
      remote_panel_subtitle: 'Control your Android TV / Google TV Streamer / Phone, type text from PC, or install .APK files over Wi-Fi',
      remote_dpad_title: '📺 D-Pad Remote & Fast PC Text Input',
      lbl_remote_text: 'Type Text / Password / Search from PC directly onto Screen:',
      btn_send_text: '⌨️ Send + Enter',
      apk_sideload_title: '📦 Wireless APK Sideloader (Drag & Drop)',
      apk_sideload_desc: 'Install any Android .apk file directly from your PC onto your Android TV, Google TV Streamer, or Phone over Wi-Fi/USB:',
      apk_drop_label: 'Click to select an .APK file or Drag & Drop it here',
      apk_drop_hint: 'Installs automatically via adb install -r',
      tv_clean_mode_title: '📺 Android TV Clean Home & AdGuard AdBlock',
      btn_tv_clean_home: '📺 Stop TV Banner Ad Services',
      btn_enable_adguard: '🛡️ Enable AdGuard AdBlock DNS',
      btn_disable_adguard: '🔄 Restore Default DNS',
      wireless_title: '📶 Wireless ADB Connection (Phones & Android TV / Google TV)',
      wireless_subtitle: 'Connect any Android 11+ phone or Android TV (:5555) directly over your local Wi-Fi network',
      btn_mdns_discover: '🔍 Auto-Discover Phones & TVs on Wi-Fi',
      btn_hide: '✕ Hide',
      wireless_steps_html: '<strong>How to enable (without cable):</strong> &bull; <strong>On Phone:</strong> Settings &rarr; Developer options &rarr; <strong>Wireless debugging</strong>. &bull; <strong>On Android TV / Google TV Streamer:</strong> Settings &rarr; System &rarr; Developer options &rarr; <strong>USB debugging</strong> (automatically opens Wi-Fi port 5555!).',
      pair_step_title: '1️⃣ First-Time Phone Setup: Pair with 6-Digit Code',
      pair_step_desc: 'On your phone, tap "Pair device with pairing code" and enter the details shown in the popup:',
      lbl_pair_ip: 'Pairing IP & Port (from phone popup):',
      lbl_pair_code: 'Wi-Fi Pairing Code (6 digits):',
      lbl_pair_conn_port: 'Connection Port (optional):',
      btn_pair_submit: '🔗 Pair & Connect Phone',
      conn_step_title: '2️⃣ Direct Connect (Android TV :5555 or Paired Phone)',
      conn_step_desc: 'For Android TV / Google TV Streamer (just enter its IP or IP:5555) or an already paired phone:',
      lbl_conn_ip: 'Device IP or IP:Port:',
      btn_conn_submit: '📶 Connect via Wi-Fi / LAN',
      btn_disconnect_wifi: '🔌 Disconnect Wi-Fi',
      live_console_title: 'Live Repair Execution Console',
      btn_close: '✕ Close',
      btn_rescan_now: '🔍 Rescan Device Now',
      btn_reboot_zram: '🔄 Reboot Device (Flush ZRAM)',
      scan_progress_label: 'Analyzing GPU frame drops (UI Jank), ANR/crash logs, bloatware, wakelocks, system SQLite databases, ZRAM swap, and storage...',
      ba_card_title: 'Before vs. After Optimization Results',
      btn_export_cert: '📄 Export Health Certificate (HTML)',
      toolbar_title: '🛠️ Quick Repair & Optimization Bar (Phone & Android TV)',
      toolbar_hint: 'Direct non-destructive ADB actions to eliminate UI stutter, unlock system databases, block ads, and free memory',
      tb_fix_all: '⚡ Fix All (Anti-Lag & Anti-Freeze)',
      tb_fix_db: '📇 Repair System Databases (Contacts / MediaStore / Sync)',
      tb_fix_zram: '🧠 Relieve ZRAM & Stop Parasitic Daemons',
      tb_fix_stutter: '🚀 Fix UI Stutter (120Hz + 0.5x Animations + Launcher)',
      tb_adguard: '🛡️ Enable AdGuard AdBlock DNS',
      tb_deep_doze: '🌙 Enable Deep Doze (Battery Saver)',
      tb_clean_junk: '📦 Deep Storage & Junk Clean',
      tb_restore_anim: '🔄 Default Animations (1.0x)',
      issues_title: 'Identified root causes for stutter & freezes:',
      recom_title: 'Tailored Repair & Action Plan',
      bloat_section_title: 'Smart Bloatware Uninstaller (Rootless + 1-Click Undo / Restore)',
      btn_remove_all_bloat: '🗑️ Remove All Detected Bloatware',
      bloat_section_desc: 'Preinstalled OEM / TV bloatware that consumes RAM and telemetry in the background. Uninstalling removes them for your user profile without Root, and you can restore any package anytime with 1 click!',
      custom_app_title: 'Universal Installed App Explorer & Repair',
      btn_load_packages: '🔄 Load Installed Apps',
      custom_app_desc: 'Have a specific app that loads slowly, freezes, or drains battery in the background? Select or type its package name below:',
      custom_pkg_placeholder: 'Search or type package name (e.g. com.whatsapp, com.stremio.one)...',
      btn_custom_repair: '🔧 Repair & Speed Compile (Keep Data)',
      btn_custom_restrict: '🛑 Restrict Background',
      btn_custom_uninstall: '🗑️ Uninstall (User 0)',
      btn_custom_restore: '♻️ Restore (Undo)',
      card_ui_title: 'UI Fluency & Display',
      lbl_jank_frames: 'Dropped Frames (Jank):',
      lbl_refresh_anim: 'Refresh Rate / Animations:',
      lbl_access_hooks: 'Accessibility Hooks:',
      card_storage_title: 'Internal Flash Storage',
      card_ram_title: 'RAM & ZRAM Swap',
      lbl_ram_used: 'Used RAM:',
      card_thermal_title: 'Thermals & Processor',
      lbl_bat_temp: 'Temperature:',
      lbl_throttle: 'Throttling Status:',
      lbl_uptime: 'System Uptime:',
      sec_card_title: '🛡️ AdGuard AdBlock DNS & Sideloaded Apps Audit',
      storage_wl_title: '📦 Storage Folders & 🔋 Active WakeLocks',
      btn_clean_junk_small: '📦 Clean Junk',
      btn_deep_doze_small: '🌙 Deep Doze',
      anr_section_title: 'Freezing & Crashing Apps (ANR / Crash in the Last 24h)',
      anr_section_desc: 'Use 🔧 Repair (Keep Data) to clear only corrupted cache and AOT-compile the app in native speed mode without wiping your account!',
      jank_section_title: 'Apps with UI Stutter (GPU Frame Drops)',
      jank_section_desc: 'These packages missed GPU frame rendering deadlines (>8.3ms at 120Hz / >16.6ms at 60Hz), causing visible scrolling stutter:',
      top_ram_title: 'Top RAM Consumers (Quick Force-Stop)',
      top_cpu_title: 'Top Active CPU Processes',
      modal_guide_title: 'How to Enable USB or Wireless Debugging on Phone & Android TV',
      btn_got_it: 'Got it'
    },
    ro: {
      header_subtitle: 'Diagnostic & reparare sacadare (UI Jank), aplicații blocate (ANR), baze de date sistem, bloatware & compilare ART (USB / Wi-Fi)',
      btn_remote_header: '🎮 Telecomandă & Instalare APK',
      btn_wireless_header: '📶 Conectare Wireless (Fără USB)',
      btn_guide: 'Ghid Activare ADB',
      lbl_active_device: 'Dispozitiv activ:',
      btn_wireless_mode: '📶 Mod Wireless Wi-Fi',
      btn_super_boost_top: '⚡ Super-Optimizare 1-Click',
      btn_scan_phone: 'Scanează Dispozitivul',
      remote_panel_title: '🎮 Telecomandă Virtuală, Tastatură PC & Instalare APK Wireless',
      remote_panel_subtitle: 'Controlează Android TV / Google TV Streamer / Telefonul, scrie text de pe tastatura PC-ului sau instalează fișiere .APK prin Wi-Fi',
      remote_dpad_title: '📺 Telecomandă D-Pad & Trimitere Rapidă Text de pe PC',
      lbl_remote_text: 'Scrie Text / Parolă / Căutare de pe PC direct pe Ecranul TV/Telefon:',
      btn_send_text: '⌨️ Trimite + Enter',
      apk_sideload_title: '📦 Instalare APK prin Wi-Fi / USB (Drag & Drop)',
      apk_sideload_desc: 'Instalează orice fișier .apk direct de pe PC pe televizorul Philips, Google TV Streamer sau telefon:',
      apk_drop_label: 'Apasă pentru a alege un fișier .APK sau trage-l cu mouse-ul aici',
      apk_drop_hint: 'Se instalează automat prin adb install -r',
      tv_clean_mode_title: '📺 Android TV Fără Reclame & AdGuard AdBlock DNS',
      btn_tv_clean_home: '📺 Oprește Serviciile de Reclame TV',
      btn_enable_adguard: '🛡️ Activează AdGuard AdBlock DNS',
      btn_disable_adguard: '🔄 Restaurează DNS Standard',
      wireless_title: '📶 Conectare Wireless ADB (Telefoane & Android TV / Google TV)',
      wireless_subtitle: 'Conectează orice telefon Android 11+ sau Android TV (:5555) direct prin rețeaua Wi-Fi locală',
      btn_mdns_discover: '🔍 Caută automat Telefoane & TV-uri în Wi-Fi',
      btn_hide: '✕ Ascunde',
      wireless_steps_html: '<strong>Cum activezi (fără cablu):</strong> &bull; <strong>Pe Telefon:</strong> Setări &rarr; Opțiuni dezvoltator &rarr; <strong>Depanare wireless</strong>. &bull; <strong>Pe Android TV / Google TV Streamer:</strong> Setări &rarr; Sistem &rarr; Opțiuni dezvoltator &rarr; <strong>Depanare USB (USB debugging)</strong> (deschide automat portul Wi-Fi 5555!).',
      pair_step_title: '1️⃣ Prima Conectare Telefon: Asociere cu Cod (6 cifre)',
      pair_step_desc: 'Pe telefon, apasă pe „Asociați dispozitivul cu un cod de asociere” și introdu datele afișate:',
      lbl_pair_ip: 'IP și Port de Asociere (din fereastra pop-up):',
      lbl_pair_code: 'Cod Asociere (6 cifre):',
      lbl_pair_conn_port: 'Port Conectare (opțional):',
      btn_pair_submit: '🔗 Asociază și Conectează Telefonul',
      conn_step_title: '2️⃣ Conectare Directă (Android TV :5555 sau Telefon Asociat)',
      conn_step_desc: 'Pentru Android TV / Google TV Streamer (introdu doar IP-ul sau IP:5555) sau un telefon deja asociat:',
      lbl_conn_ip: 'IP sau IP:Port Dispozitiv:',
      btn_conn_submit: '📶 Conectează prin Wi-Fi / LAN',
      btn_disconnect_wifi: '🔌 Deconectează Wi-Fi',
      live_console_title: 'Consolă Execuție Reparații Live',
      btn_close: '✕ Închide',
      btn_rescan_now: '🔍 Re-scanează Dispozitivul Acum',
      btn_reboot_zram: '🔄 Restart Dispozitiv (Golire ZRAM)',
      scan_progress_label: 'Se analizează cadrele pierdute (UI Jank), jurnalele ANR, bloatware-ul, wakelocks, bazele de date, ZRAM și stocarea...',
      ba_card_title: 'Comparație Rezultate Înainte vs. După Optimizare',
      btn_export_cert: '📄 Exportă Certificat Sănătate (HTML)',
      toolbar_title: '🛠️ Panou de Intervenție Rapidă (Telefon & Android TV)',
      toolbar_hint: 'Acțiuni directe prin ADB pentru eliminarea sacadării, deblocarea bazelor de date, blocarea reclamelor și optimizarea memoriei',
      tb_fix_all: '⚡ Repară Tot (Anti-Lag & Anti-Freeze)',
      tb_fix_db: '📇 Repară Baze de Date Sistem (Contacte / MediaStore / Sync)',
      tb_fix_zram: '🧠 Deblocare ZRAM & Stop Servicii Parazite',
      tb_fix_stutter: '🚀 Elimină Sacadarea (120Hz + Animații 0.5x + Launcher)',
      tb_adguard: '🛡️ Activează AdGuard AdBlock DNS',
      tb_deep_doze: '🌙 Activează Deep Doze (Economie Baterie)',
      tb_clean_junk: '📦 Curățare Profundă Stocare & Fișiere Reziduale',
      tb_restore_anim: '🔄 Animații 1.0x (Standard)',
      issues_title: 'Cauzele identificate pentru sacadare și blocaje:',
      recom_title: 'Plan de Reparare Personalizat',
      bloat_section_title: 'Dezinstalare Sigură Bloatware (Fără Root + Buton Undo / Restaurare 1-Clic)',
      btn_remove_all_bloat: '🗑️ Elimină Tot Bloatware-ul Detectat',
      bloat_section_desc: 'Aplicații preinstalate inutile (OEM / TV) care consumă RAM și trimit telemetrie în fundal. Dezinstalarea le elimină fără Root, iar cu butonul ♻️ Restaurează (Undo) le poți aduce înapoi oricând!',
      custom_app_title: 'Reparare & Optimizare pentru Orice Aplicație Instalată',
      btn_load_packages: '🔄 Încarcă Lista Aplicațiilor',
      custom_app_desc: 'Ai o aplicație care se deschide greu, îngheață sau consumă bateria în fundal? Selecteaz-o sau scrie numele pachetului mai jos:',
      custom_pkg_placeholder: 'Caută sau scrie un pachet (ex: com.whatsapp, com.stremio.one)...',
      btn_custom_repair: '🔧 Repară & Compilează Speed (Fără pierdere date)',
      btn_custom_restrict: '🛑 Restricționează Fundal',
      btn_custom_uninstall: '🗑️ Dezinstalează (User 0)',
      btn_custom_restore: '♻️ Restaurează (Undo)',
      card_ui_title: 'Fluență UI & Ecran',
      lbl_jank_frames: 'Cadre Pierdute (Jank):',
      lbl_refresh_anim: 'Rată Refresh / Animații:',
      lbl_access_hooks: 'Hook-uri Accesibilitate:',
      card_storage_title: 'Stocare Internă Flash',
      card_ram_title: 'Memorie RAM & ZRAM',
      lbl_ram_used: 'RAM Utilizat:',
      card_thermal_title: 'Termice & Procesor',
      lbl_bat_temp: 'Temperatură:',
      lbl_throttle: 'Stare Throttling:',
      lbl_uptime: 'Timp fără Restart:',
      sec_card_title: '🛡️ AdGuard AdBlock DNS & Audit Aplicații Sideloaded',
      storage_wl_title: '📦 Top Foldere Stocare & 🔋 WakeLocks Active',
      btn_clean_junk_small: '📦 Curăță Junk',
      btn_deep_doze_small: '🌙 Deep Doze',
      anr_section_title: 'Aplicații care se Blochează (ANR / Crash / Înghețare în ultimele 24h)',
      anr_section_desc: 'Folosește butonul 🔧 Repară (Păstrează Date) pentru a curăța doar cache-ul corupt și a recompila nativ aplicația în mod speed (fără să îți șteargă contul!).',
      jank_section_title: 'Aplicații cu Mișcare Sacadată (Frame Drops / Lag Grafic)',
      jank_section_desc: 'Aceste aplicații au întârziat randarea cadrelor pe ecran (peste 8.3ms / 16.6ms), provocând senzația de agățare sau scroll sacadat:',
      top_ram_title: 'Top Consumatori Memorie RAM (Cu oprire rapidă)',
      top_cpu_title: 'Top Consumatori CPU Recenți (Procese active)',
      modal_guide_title: 'Cum activezi Depanarea USB sau Wireless pe Telefon & Android TV',
      btn_got_it: 'Am înțeles'
    }
  };

  function isRo() {
    return currentLang === 'ro';
  }

  function applyStaticTranslations() {
    const dict = I18N[currentLang] || I18N.en;
    document.documentElement.lang = currentLang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.textContent = dict[key];
      }
    });
    const stepsBanner = document.getElementById('wirelessStepsBanner');
    if (stepsBanner && dict.wireless_steps_html) {
      stepsBanner.innerHTML = dict.wireless_steps_html;
    }
    const customInput = document.getElementById('customPkgInput');
    if (customInput && dict.custom_pkg_placeholder) {
      customInput.placeholder = dict.custom_pkg_placeholder;
    }
    const langLabel = document.getElementById('langToggleLabel');
    if (langLabel) {
      langLabel.innerHTML = currentLang === 'en'
        ? '<strong>🇬🇧 EN</strong> | <span style="opacity:0.6">🇷🇴 RO</span>'
        : '<span style="opacity:0.6">🇬🇧 EN</span> | <strong>🇷🇴 RO</strong>';
    }
  }

  window.toggleLanguage = function() {
    currentLang = currentLang === 'en' ? 'ro' : 'en';
    localStorage.setItem('ahd_lang', currentLang);
    applyStaticTranslations();
    checkDeviceStatus();
    if (lastScanReport && activeDevice) {
      triggerScan();
    }
  };

  // DOM elements
  const connectionCard = document.getElementById('connectionCard');
  const connStatusTitle = document.getElementById('connStatusTitle');
  const connStatusDesc = document.getElementById('connStatusDesc');
  const deviceSelectorWrap = document.getElementById('deviceSelectorWrap');
  const deviceSelector = document.getElementById('deviceSelector');
  const phoneLiveActivityBadge = document.getElementById('phoneLiveActivityBadge');
  const phoneLiveActivityDot = document.getElementById('phoneLiveActivityDot');
  const phoneLiveActivityText = document.getElementById('phoneLiveActivityText');
  const scanBtn = document.getElementById('scanBtn');
  const superBoostTopBtn = document.getElementById('superBoostTopBtn');
  const scanProgressBar = document.getElementById('scanProgressBar');
  const resultsArea = document.getElementById('resultsArea');
  const wirelessCard = document.getElementById('wirelessCard');
  const remoteCard = document.getElementById('remoteCard');
  const toggleWirelessBtn = document.getElementById('toggleWirelessBtn');
  const wirelessStatusMsg = document.getElementById('wirelessStatusMsg');
  const mdnsDiscoveryBox = document.getElementById('mdnsDiscoveryBox');

  // Live Console elements
  const liveConsoleCard = document.getElementById('liveConsoleCard');
  const liveStatusBadge = document.getElementById('liveStatusBadge');
  const liveStepCounter = document.getElementById('liveStepCounter');
  const liveElapsedTimer = document.getElementById('liveElapsedTimer');
  const closeLiveConsoleBtn = document.getElementById('closeLiveConsoleBtn');
  const liveProgressBarFill = document.getElementById('liveProgressBarFill');
  const liveCurrentTaskBox = document.getElementById('liveCurrentTaskBox');
  const liveLogContainer = document.getElementById('liveLogContainer');
  const liveFinishBanner = document.getElementById('liveFinishBanner');
  const liveFinishText = document.getElementById('liveFinishText');

  // Modal elements
  const guideBtn = document.getElementById('guideBtn');
  const guideModal = document.getElementById('guideModal');
  const closeGuideBtn = document.getElementById('closeGuideBtn');
  const guideGotItBtn = document.getElementById('guideGotItBtn');
  const toast = document.getElementById('toast');

  applyStaticTranslations();

  guideBtn.addEventListener('click', () => guideModal.classList.remove('hidden'));
  closeGuideBtn.addEventListener('click', () => guideModal.classList.add('hidden'));
  guideGotItBtn.addEventListener('click', () => guideModal.classList.add('hidden'));
  if (closeLiveConsoleBtn) {
    closeLiveConsoleBtn.addEventListener('click', () => liveConsoleCard.classList.add('hidden'));
  }
  if (toggleWirelessBtn) {
    toggleWirelessBtn.addEventListener('click', () => window.toggleWirelessPanel());
  }
  if (deviceSelector) {
    deviceSelector.addEventListener('change', (e) => {
      selectedSerial = e.target.value;
      checkDeviceStatus();
    });
  }

  // APK Drag & Drop events
  const apkDropzone = document.getElementById('apkDropzone');
  if (apkDropzone) {
    apkDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      apkDropzone.classList.add('dragover');
    });
    apkDropzone.addEventListener('dragleave', () => apkDropzone.classList.remove('dragover'));
    apkDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      apkDropzone.classList.remove('dragover');
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        window.handleApkFileSelect(e.dataTransfer.files);
      }
    });
  }

  window.toggleRemotePanel = function() {
    if (!remoteCard) return;
    remoteCard.classList.toggle('hidden');
  };

  window.sendRemoteKey = async function(keycode) {
    try {
      await fetch('/api/remote/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keycode: keycode,
          serial: activeDevice ? activeDevice.serial : null,
          lang: currentLang
        })
      });
    } catch (e) {
      console.error('Remote key error:', e);
    }
  };

  window.sendRemoteText = async function(submitEnter = true) {
    const inp = document.getElementById('remoteTextInput');
    const txt = (inp?.value || '').trim();
    if (!txt) return;
    try {
      const res = await fetch('/api/remote/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: txt,
          submit_enter: submitEnter,
          serial: activeDevice ? activeDevice.serial : null,
          lang: currentLang
        })
      });
      const data = await res.json();
      if (data.success) {
        inp.value = '';
        showToast(data.message || 'Text sent!');
      }
    } catch (e) {
      console.error('Remote text error:', e);
    }
  };

  window.handleApkFileSelect = async function(files) {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (liveConsoleCard) {
      liveConsoleCard.classList.remove('hidden');
      liveFinishBanner.classList.add('hidden');
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = isRo() ? '🔄 INSTALARE APK...' : '🔄 INSTALLING APK...';
      liveProgressBarFill.style.width = '20%';
      liveCurrentTaskBox.textContent = `${isRo() ? 'Se încarcă și se instalează' : 'Uploading & installing'} ${file.name}...`;
      liveConsoleCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    try {
      const qs = new URLSearchParams({
        filename: file.name,
        serial: activeDevice ? activeDevice.serial : '',
        lang: currentLang
      });
      const res = await fetch(`/api/install-apk?${qs.toString()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: file
      });
      if (!res.ok) throw new Error('APK upload failed');
      startJobPolling();
    } catch (err) {
      alert('APK Install Error: ' + err.message);
    }
  };

  window.toggleWirelessPanel = function() {
    if (!wirelessCard) return;
    wirelessCard.classList.toggle('hidden');
    if (!wirelessCard.classList.contains('hidden')) {
      window.discoverWirelessPhones();
    }
  };

  function showWirelessMessage(msg, isError = false) {
    if (!wirelessStatusMsg) return;
    wirelessStatusMsg.classList.remove('hidden');
    wirelessStatusMsg.style.borderColor = isError ? 'rgba(234, 67, 53, 0.5)' : 'rgba(52, 168, 83, 0.5)';
    wirelessStatusMsg.style.color = isError ? '#fca5a5' : '#86efac';
    wirelessStatusMsg.textContent = msg;
  }

  window.discoverWirelessPhones = async function() {
    if (!mdnsDiscoveryBox) return;
    mdnsDiscoveryBox.classList.remove('hidden');
    mdnsDiscoveryBox.innerHTML = isRo()
      ? '<span style="color:#93c5fd;">🔍 Se scanează rețeaua Wi-Fi pentru telefoane (mDNS) și Android TV / Google TV (Port 5555)...</span>'
      : '<span style="color:#93c5fd;">🔍 Scanning Wi-Fi network for phones (mDNS) and Android TV / Google TV devices (Port 5555)...</span>';
    try {
      const res = await fetch(`/api/wireless/discover?lang=${currentLang}`);
      const data = await res.json();
      const pairs = data.pairing_services || [];
      const connects = data.connect_services || [];

      if (pairs.length === 0 && connects.length === 0) {
        mdnsDiscoveryBox.innerHTML = isRo()
          ? '<span style="color:#94a3b8;">Niciun dispozitiv detectat automat. Activează <strong>Depanare wireless</strong> (pe telefon) sau <strong>Depanare USB</strong> (pe Android TV) ori introdu IP-ul manual mai jos.</span>'
          : '<span style="color:#94a3b8;">No device auto-detected yet. Enable <strong>Wireless debugging</strong> (on phone) or <strong>USB debugging</strong> (on Android TV) or enter the IP manually below.</span>';
        return;
      }

      let html = '<div style="display:flex; flex-direction:column; gap:8px;">';
      pairs.forEach(p => {
        const lbl = isRo() ? '🔑 Detectat în mod Asociere (Pair):' : '🔑 Detected in Pairing Mode:';
        const btnLbl = isRo() ? 'Completează IP:Port Asociere' : 'Fill Pairing IP:Port';
        html += `<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="color:#fde047;">${lbl} <strong>${escapeHtml(p.address)}</strong></span>
          <button class="btn btn-action-small" onclick="document.getElementById('pairAddrInput').value='${escapeHtml(p.address)}'; document.getElementById('pairCodeInput').focus();">${btnLbl}</button>
        </div>`;
        const pairInput = document.getElementById('pairAddrInput');
        if (pairInput && !pairInput.value) pairInput.value = p.address;
      });

      connects.forEach(c => {
        const lbl = isRo() ? '📶 Dispozitiv Android / TV Detectat în Wi-Fi:' : '📶 Android / TV Device Detected on Wi-Fi:';
        const btnLbl = isRo() ? 'Conectează cu 1-Clic' : '1-Click Connect';
        html += `<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="color:#4ade80;">${lbl} <strong>${escapeHtml(c.address)}</strong></span>
          <button class="btn btn-action-small" onclick="document.getElementById('connectAddrInput').value='${escapeHtml(c.address)}'; window.submitWirelessConnect();">${btnLbl}</button>
        </div>`;
        const connInput = document.getElementById('connectAddrInput');
        if (connInput && !connInput.value) connInput.value = c.address;
        const pairConnPort = document.getElementById('pairConnectPortInput');
        if (pairConnPort && !pairConnPort.value) pairConnPort.value = c.port;
      });
      html += '</div>';
      mdnsDiscoveryBox.innerHTML = html;
    } catch (e) {
      mdnsDiscoveryBox.innerHTML = isRo()
        ? '<span style="color:#f87171;">Eroare la căutarea în rețea. Poți introduce IP-ul manual mai jos.</span>'
        : '<span style="color:#f87171;">Network discovery error. You can enter the IP manually below.</span>';
    }
  };

  window.submitWirelessPair = async function() {
    const pairAddr = (document.getElementById('pairAddrInput')?.value || '').trim();
    const pairCode = (document.getElementById('pairCodeInput')?.value || '').trim();
    const connPort = (document.getElementById('pairConnectPortInput')?.value || '').trim();

    if (!pairAddr || !pairCode) {
      showWirelessMessage(
        isRo()
          ? 'Te rugăm să introduci atât IP:Port de asociere, cât și codul din 6 cifre afișat pe telefon!'
          : 'Please enter both the Pairing IP:Port and the 6-digit pairing code shown on your phone!',
        true
      );
      return;
    }

    showWirelessMessage(isRo() ? '⏳ Se asociază cu telefonul prin Wi-Fi...' : '⏳ Pairing with phone over Wi-Fi...');
    try {
      const res = await fetch('/api/wireless/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pairing_addr: pairAddr,
          pairing_code: pairCode,
          connect_addr: connPort || null,
          lang: currentLang
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Pairing failed');

      showWirelessMessage(data.message, false);
      showToast(data.message, 6000);
      if (data.ip && document.getElementById('connectAddrInput') && !document.getElementById('connectAddrInput').value) {
        document.getElementById('connectAddrInput').value = `${data.ip}:`;
      }
      await checkDeviceStatus();
    } catch (err) {
      showWirelessMessage('❌ ' + err.message, true);
    }
  };

  window.submitWirelessConnect = async function() {
    const connAddr = (document.getElementById('connectAddrInput')?.value || '').trim();
    if (!connAddr) {
      showWirelessMessage(
        isRo()
          ? 'Introdu Adresa IP sau IP:Port (ex: 192.168.86.48:5555).'
          : 'Enter the IP address or IP:Port (e.g. 192.168.86.48:5555).',
        true
      );
      return;
    }

    showWirelessMessage(isRo() ? '⏳ Se conectează prin Wi-Fi/LAN...' : '⏳ Connecting via Wi-Fi/LAN...');
    try {
      const res = await fetch('/api/wireless/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connect_addr: connAddr, lang: currentLang })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Connection failed');

      showWirelessMessage(data.message, false);
      showToast(data.message, 5000);
      selectedSerial = data.address;
      await checkDeviceStatus();
    } catch (err) {
      showWirelessMessage('❌ ' + err.message, true);
    }
  };

  window.disconnectWirelessAll = async function() {
    try {
      const res = await fetch('/api/wireless/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: currentLang })
      });
      const data = await res.json();
      showWirelessMessage(data.message || 'Disconnected.', false);
      await checkDeviceStatus();
    } catch (err) {
      showWirelessMessage('Disconnect error: ' + err.message, true);
    }
  };

  function showToast(msg, duration = 4500) {
    toast.textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, duration);
  }

  function updatePhoneActivityUI(phoneActivity) {
    if (!phoneLiveActivityBadge || !phoneActivity) return;
    phoneLiveActivityBadge.classList.remove('hidden');
    if (phoneActivity.busy) {
      phoneLiveActivityBadge.className = 'phone-activity-pill activity-busy';
      phoneLiveActivityDot.className = 'activity-dot busy';
      phoneLiveActivityText.textContent = isRo()
        ? `⚙️ Dispozitivul lucrează acum: ${phoneActivity.summary}`
        : `⚙️ Device busy: ${phoneActivity.summary}`;
    } else {
      phoneLiveActivityBadge.className = 'phone-activity-pill activity-idle';
      phoneLiveActivityDot.className = 'activity-dot idle';
      phoneLiveActivityText.textContent = isRo()
        ? '🟢 Stare procese dispozitiv: În repaus (toate optimizările din fundal s-au terminat)'
        : '🟢 Device background status: Idle (all background tasks completed)';
    }
  }

  async function checkDeviceStatus() {
    try {
      const res = await fetch(`/api/status?lang=${currentLang}`);
      const data = await res.json();

      if (!data.adb_available) {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = isRo() ? 'ADB nu este instalat sau găsit' : 'ADB not installed or not found';
        connStatusDesc.textContent = isRo() ? 'Verifică dacă Android Platform Tools este instalat.' : 'Verify that Android Platform Tools (adb) is installed.';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
        return;
      }

      if (!data.devices || data.devices.length === 0) {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = isRo() ? 'Niciun telefon sau TV conectat (USB sau Wi-Fi)' : 'No Android Phone or TV connected (USB or Wi-Fi)';
        connStatusDesc.textContent = isRo()
          ? 'Conectează prin cablu USB sau apasă pe „📶 Mod Wireless Wi-Fi” pentru conectare fără cablu.'
          : 'Connect via USB cable or click "📶 Wireless Wi-Fi Mode" for cable-free connection.';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        if (deviceSelectorWrap) deviceSelectorWrap.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
        activeDevice = null;
        return;
      }

      const authorizedDevices = data.devices.filter(d => d.state === 'device');
      const unauthorizedDevice = data.devices.find(d => d.state === 'unauthorized');

      if (authorizedDevices.length > 0) {
        if (deviceSelectorWrap && deviceSelector) {
          if (authorizedDevices.length > 1) {
            deviceSelectorWrap.classList.remove('hidden');
            const currentOptions = Array.from(deviceSelector.options).map(o => o.value).join(',');
            const newOptions = authorizedDevices.map(d => d.serial).join(',');
            if (currentOptions !== newOptions) {
              deviceSelector.innerHTML = '';
              authorizedDevices.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.serial;
                opt.textContent = `${d.model} (${d.serial}) [${d.connection_type || (d.is_wireless ? 'Wi-Fi' : 'USB')}]`;
                deviceSelector.appendChild(opt);
              });
            }
            if (selectedSerial && authorizedDevices.some(d => d.serial === selectedSerial)) {
              deviceSelector.value = selectedSerial;
            }
          } else {
            deviceSelectorWrap.classList.add('hidden');
          }
        }

        const chosenDevice = (selectedSerial && authorizedDevices.find(d => d.serial === selectedSerial)) || authorizedDevices[0];
        activeDevice = chosenDevice;
        const connIcon = chosenDevice.is_wireless ? '📶 Wi-Fi / LAN' : (isRo() ? '🔌 Cablu USB' : '🔌 USB Cable');
        connectionCard.className = 'card connection-card state-connected';
        connStatusTitle.textContent = isRo()
          ? `Conectat (${connIcon}): ${chosenDevice.model} [${chosenDevice.serial}]`
          : `Connected (${connIcon}): ${chosenDevice.model} [${chosenDevice.serial}]`;
        connStatusDesc.textContent = isRo()
          ? 'Dispozitivul este autorizat și gata pentru scanare sau optimizare rapidă.'
          : 'Device is authorized and ready for deep diagnostic scan or 1-Click optimization.';
        scanBtn.disabled = false;
        if (superBoostTopBtn) superBoostTopBtn.disabled = false;
        updatePhoneActivityUI(data.phone_activity);

        if (data.job_running && !jobPollInterval) {
          startJobPolling();
        }
      } else if (unauthorizedDevice) {
        activeDevice = unauthorizedDevice;
        connectionCard.className = 'card connection-card state-unauthorized';
        connStatusTitle.textContent = isRo()
          ? `Dispozitiv detectat (${unauthorizedDevice.serial}) - Necesită autorizare pe ecran`
          : `Device detected (${unauthorizedDevice.serial}) - Screen authorization required`;
        connStatusDesc.textContent = isRo()
          ? 'Privește ecranul telefonului sau televizorului și apasă pe "Permiteți" (Allow USB debugging).'
          : 'Look at your phone or TV screen and press "Allow" on the USB debugging prompt.';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
      } else {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = isRo() ? 'Dispozitiv în stare offline' : 'Device offline';
        connStatusDesc.textContent = isRo() ? 'Reconectează cablul USB sau conexiunea Wi-Fi.' : 'Reconnect the USB cable or Wi-Fi connection.';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
      }
    } catch (err) {
      console.error('Error fetching status:', err);
    }
  }

  async function triggerScan() {
    scanBtn.disabled = true;
    scanProgressBar.classList.remove('hidden');

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          serial: activeDevice ? activeDevice.serial : null,
          lang: currentLang
        })
      });

      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try {
          const errData = JSON.parse(text);
          detail = errData.detail || text;
        } catch (_) {}
        throw new Error(detail || 'Scan failed');
      }

      const report = await res.json();
      lastScanReport = report;
      renderReport(report);
      showToast(isRo() ? 'Scanare profundă finalizată! Rezultatele au fost actualizate.' : 'Deep diagnostic scan completed! Results updated.');
    } catch (err) {
      alert((isRo() ? 'Eroare la scanare: ' : 'Error scanning device: ') + err.message);
    } finally {
      scanBtn.disabled = false;
      scanProgressBar.classList.add('hidden');
    }
  }

  scanBtn.addEventListener('click', triggerScan);

  window.triggerRescanFromConsole = function() {
    triggerScan();
  };

  function renderBeforeAfter(report) {
    const baCard = document.getElementById('beforeAfterCard');
    const baGrid = document.getElementById('beforeAfterGrid');
    if (!baCard || !baGrid) return;

    const base = report.before_baseline;
    if (!base) {
      baCard.classList.add('hidden');
      return;
    }

    const curScore = (report.health_evaluation || {}).score || 0;
    const curRam = (report.memory || {}).available_mb || 0;
    const curZram = (report.memory || {}).swap_used_mb || 0;
    const curJank = (report.ui_fluency || {}).global_jank_percent || 0;

    const scoreDiff = curScore - (base.score || 0);
    const ramDiff = curRam - (base.available_mb || 0);
    const zramDiff = (base.swap_used_mb || 0) - curZram;
    const jankDiff = round1((base.global_jank_percent || 0) - curJank);

    if (scoreDiff === 0 && Math.abs(ramDiff) < 15 && Math.abs(jankDiff) < 0.5) {
      baCard.classList.add('hidden');
      return;
    }

    baCard.classList.remove('hidden');
    baGrid.innerHTML = `
      <div class="ba-box">
        <div class="ba-label">${isRo() ? 'Scor Sănătate' : 'Health Score'}</div>
        <div class="ba-values">${base.score}/100 &rarr; <span style="color:#4ade80;">${curScore}/100</span></div>
        <div class="ba-gain">${scoreDiff >= 0 ? '+' + scoreDiff : scoreDiff} pct</div>
      </div>
      <div class="ba-box">
        <div class="ba-label">${isRo() ? 'Memorie RAM Liberă' : 'Available RAM'}</div>
        <div class="ba-values">${base.available_mb} MB &rarr; <span style="color:#4ade80;">${curRam} MB</span></div>
        <div class="ba-gain">${ramDiff >= 0 ? '+' + ramDiff : ramDiff} MB</div>
      </div>
      <div class="ba-box">
        <div class="ba-label">${isRo() ? 'Presiune ZRAM Swap' : 'ZRAM Swap Used'}</div>
        <div class="ba-values">${base.swap_used_mb} MB &rarr; <span style="color:#93c5fd;">${curZram} MB</span></div>
        <div class="ba-gain">${zramDiff >= 0 ? '-' + zramDiff + ' MB eliberați' : '+' + Math.abs(zramDiff) + ' MB'}</div>
      </div>
      <div class="ba-box">
        <div class="ba-label">${isRo() ? 'Sacadare UI (Frame Jank)' : 'UI Frame Drops (Jank)'}</div>
        <div class="ba-values">${base.global_jank_percent}% &rarr; <span style="color:#4ade80;">${curJank}%</span></div>
        <div class="ba-gain">${jankDiff >= 0 ? '-' + jankDiff + '% jank' : ''}</div>
      </div>
    `;
  }

  function round1(v) {
    return Math.round(v * 10) / 10;
  }

  window.exportHealthCertificate = function() {
    if (!lastScanReport) return;
    const r = lastScanReport;
    const dev = r.device || {};
    const ev = r.health_evaluation || {};
    const mem = r.memory || {};
    const st = r.storage || {};
    const bat = r.battery || {};
    const ui = r.ui_fluency || {};

    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Android Health Certificate - ${escapeHtml(dev.model)}</title>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; padding: 36px; max-width: 820px; margin: auto; }
  .cert-box { background: #1e293b; border: 2px solid #3b82f6; border-radius: 16px; padding: 28px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }
  h1 { margin: 0 0 6px 0; color: #93c5fd; }
  .score { font-size: 3rem; font-weight: 800; color: #4ade80; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 20px; }
  .item { background: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #334155; }
  .lbl { color: #94a3b8; font-size: 0.82rem; }
  .val { font-size: 1.05rem; font-weight: 700; margin-top: 4px; }
</style></head><body>
  <div class="cert-box">
    <h1>🩺 Android Health & Performance Certificate</h1>
    <p style="color:#94a3b8;">Generated on ${escapeHtml(r.timestamp)} by Android Health Doctor</p>
    <div style="display:flex; align-items:center; justify-content:space-between; margin: 18px 0; padding: 16px; background:#0f172a; border-radius:12px;">
      <div>
        <div style="font-size:1.4rem; font-weight:700;">${escapeHtml(dev.brand)} ${escapeHtml(dev.model)} (${escapeHtml(dev.codename)})</div>
        <div style="color:#94a3b8;">Android ${escapeHtml(dev.android_version)} • Chipset: ${escapeHtml(dev.soc)} • Patch: ${escapeHtml(dev.security_patch)}</div>
      </div>
      <div class="score">${ev.score}/100</div>
    </div>
    <div class="grid">
      <div class="item"><div class="lbl">Verdict</div><div class="val">${escapeHtml(ev.verdict)}</div></div>
      <div class="item"><div class="lbl">RAM & ZRAM</div><div class="val">${mem.available_mb} MB Free / ${mem.total_mb} MB Total (ZRAM: ${mem.swap_percent_used}%)</div></div>
      <div class="item"><div class="lbl">Internal Flash Storage</div><div class="val">${st.free_gb} GB Free / ${st.total_gb} GB Total (${st.percent_used}% Used)</div></div>
      <div class="item"><div class="lbl">Battery Health & Cycles</div><div class="val">${escapeHtml(bat.health)} • Level: ${bat.level}% • Cycles: ${escapeHtml(String(bat.cycles))}</div></div>
      <div class="item"><div class="lbl">Display & UI Fluency</div><div class="val">${ui.peak_refresh_rate}Hz • Animations ${ui.window_animation_scale}x • Global Jank: ${ui.global_jank_percent}%</div></div>
      <div class="item"><div class="lbl">System Stability (24h)</div><div class="val">${(r.anrs_and_crashes || {}).total_anrs || 0} ANRs • ${(r.anrs_and_crashes || {}).total_crashes || 0} Crashes</div></div>
    </div>
  </div>
</body></html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Health_Certificate_${(dev.model || 'Android').replace(/\s+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  function renderReport(report) {
    resultsArea.classList.remove('hidden');
    renderBeforeAfter(report);

    const evalData = report.health_evaluation || {};
    const dev = report.device || {};
    const storage = report.storage || {};
    const storageBreakdown = report.storage_breakdown || {};
    const memory = report.memory || {};
    const anrs = report.anrs_and_crashes || {};
    const thermals = report.thermals_and_cpu || {};
    const uiFluency = report.ui_fluency || {};
    const sysPressure = report.system_pressure || {};
    const bloatware = report.bloatware || {};
    const batteryDrain = report.battery_drain || {};
    const securityAudit = report.security_audit || {};

    const scoreVal = evalData.score || 0;
    const scoreEl = document.getElementById('scoreValue');
    scoreEl.textContent = scoreVal;

    const badgeEl = document.getElementById('scoreBadge');
    badgeEl.className = `badge ${evalData.badge_class || 'info'}`;
    badgeEl.textContent = evalData.verdict || (isRo() ? 'Rezultat' : 'Result');

    document.getElementById('scoreTitle').textContent = `${dev.brand ? dev.brand + ' ' : ''}${dev.model || 'Android'} - ${evalData.verdict}`;
    document.getElementById('scoreSummary').textContent = `Android ${dev.android_version || ''} | SoC: ${dev.soc || 'ARM64'} | Patch: ${dev.security_patch || 'N/A'} | Uptime: ${dev.uptime_str || 'N/A'}`;
    const socTitle = document.getElementById('socCardTitle');
    if (socTitle) {
      socTitle.textContent = isRo()
        ? `Termice & Procesor (${dev.soc || 'SoC'})`
        : `Thermals & Processor (${dev.soc || 'SoC'})`;
    }
    window.loadInstalledPackages(true);

    // Issues list
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    const issues = evalData.issues || [];
    if (issues.length === 0) {
      issuesList.innerHTML = isRo()
        ? '<li style="color:#4ade80;">Nu au fost detectate probleme critice de performanță!</li>'
        : '<li style="color:#4ade80;">No critical performance issues detected!</li>';
    } else {
      issues.forEach(iss => {
        const li = document.createElement('li');
        li.textContent = iss;
        issuesList.appendChild(li);
      });
    }

    // Recommendations
    const recomList = document.getElementById('recommendationsList');
    recomList.innerHTML = '';
    const recommendations = evalData.recommendations || [];

    const actionButtonMap = isRo() ? {
      'deep_boost_all': { label: '⚡ Super-Optimizare Completă', cls: 'btn-accent' },
      'fix_contacts_acore': { label: '📇 Repară Baze Date Sistem (Contacte/Media)', cls: 'btn-action-small' },
      'debloat_pixel8': { label: '🧠 Deblocare ZRAM & Stop Servicii Parazite', cls: 'btn-action-small' },
      'fix_ui_stutter': { label: '🚀 Elimină Sacadarea (120Hz + 0.5x)', cls: 'btn-action-small' },
      'disable_accessibility': { label: '🛡️ Dezactivează Accesibilitate', cls: 'btn-action-small' },
      'deep_repair_app': { label: '🔧 Repară Aplicația (Păstrează Date)', cls: 'btn-action-small' },
      'fstrim': { label: '💾 Trim Flash & Curățare Cache', cls: 'btn-action-small' },
      'storage_clean': { label: '💾 Trim Flash & Curățare Cache', cls: 'btn-action-small' },
      'optimize_ram': { label: '🧹 Eliberează RAM & Fundal', cls: 'btn-action-small' },
      'cool_down': { label: '❄️ Oprește Consumatori CPU', cls: 'btn-action-small' },
      'art_optimize': { label: '⚙️ Compilare ART Speed', cls: 'btn-action-small' },
      'clear_package_cache': { label: '🗑️ Reset Complet Aplicație', cls: 'btn-action-small' },
      'reboot': { label: '🔄 Restart Dispozitiv', cls: 'btn-action-small' }
    } : {
      'deep_boost_all': { label: '⚡ Complete Super Boost', cls: 'btn-accent' },
      'fix_contacts_acore': { label: '📇 Rebuild System DBs (Contacts/Media)', cls: 'btn-action-small' },
      'debloat_pixel8': { label: '🧠 Relieve ZRAM & Stop Parasitic Daemons', cls: 'btn-action-small' },
      'fix_ui_stutter': { label: '🚀 Fix UI Stutter (120Hz + 0.5x)', cls: 'btn-action-small' },
      'disable_accessibility': { label: '🛡️ Disable Accessibility Hooks', cls: 'btn-action-small' },
      'deep_repair_app': { label: '🔧 Repair App (Keep Data)', cls: 'btn-action-small' },
      'fstrim': { label: '💾 Flash TRIM & Cache Clean', cls: 'btn-action-small' },
      'storage_clean': { label: '💾 Flash TRIM & Cache Clean', cls: 'btn-action-small' },
      'optimize_ram': { label: '🧹 Free RAM & Background', cls: 'btn-action-small' },
      'cool_down': { label: '❄️ Stop CPU Hogs', cls: 'btn-action-small' },
      'art_optimize': { label: '⚙️ ART Speed Compile', cls: 'btn-action-small' },
      'clear_package_cache': { label: '🗑️ Full App Reset', cls: 'btn-action-small' },
      'reboot': { label: '🔄 Reboot Device', cls: 'btn-action-small' }
    };

    recommendations.forEach(rec => {
      const item = document.createElement('div');
      item.className = `recom-item ${rec.severity || 'recomandat'}`;

      let btnHtml = '';
      const cfg = actionButtonMap[rec.action_type];
      if (cfg) {
        const pkgArg = rec.package ? `, '${escapeHtml(rec.package)}'` : '';
        btnHtml = `<button class="btn ${cfg.cls}" onclick="executeOptimization('${rec.action_type}'${pkgArg})">${cfg.label}</button>`;
      }

      item.innerHTML = `
        <div class="recom-text">
          <h5>${escapeHtml(rec.title)}</h5>
          <p>${escapeHtml(rec.description)}</p>
        </div>
        <div class="recom-btn-wrap">
          ${btnHtml}
        </div>
      `;
      recomList.appendChild(item);
    });

    // Smart Bloatware List (Active + Removed with Undo)
    const bloatListEl = document.getElementById('bloatwareList');
    const bloatBadge = document.getElementById('bloatCountBadge');
    const actBloat = bloatware.active_bloatware || [];
    const remBloat = bloatware.removed_bloatware || [];
    if (bloatBadge) {
      bloatBadge.textContent = isRo()
        ? `${actBloat.length} Active / ${remBloat.length} Dezinstalate`
        : `${actBloat.length} Active / ${remBloat.length} Removed`;
      bloatBadge.className = `badge ${actBloat.length > 0 ? 'warning' : 'success'}`;
    }
    if (bloatListEl) {
      bloatListEl.innerHTML = '';
      if (actBloat.length === 0 && remBloat.length === 0) {
        bloatListEl.innerHTML = `<div style="padding:14px; color:#4ade80; text-align:center;">${isRo() ? 'Nu s-a detectat bloatware preinstalat pe acest dispozitiv!' : 'No known preinstalled bloatware detected on this device!'}</div>`;
      } else {
        actBloat.forEach(b => {
          const pkg = escapeHtml(b.package);
          const row = document.createElement('div');
          row.className = 'anr-row';
          row.innerHTML = `
            <div>
              <div class="anr-pkg" style="color:#fde047;">${pkg}</div>
              <div class="anr-meta">${escapeHtml(b.description)}</div>
            </div>
            <div class="row-actions">
              <button class="btn btn-action-small btn-danger-small" onclick="executeOptimization('debloat_uninstall', '${pkg}')">🗑️ ${isRo() ? 'Dezinstalează (Fără Root)' : 'Uninstall (Rootless)'}</button>
            </div>
          `;
          bloatListEl.appendChild(row);
        });
        remBloat.forEach(b => {
          const pkg = escapeHtml(b.package);
          const row = document.createElement('div');
          row.className = 'anr-row';
          row.style.opacity = '0.75';
          row.innerHTML = `
            <div>
              <div class="anr-pkg" style="color:#86efac; text-decoration: line-through;">${pkg}</div>
              <div class="anr-meta">${escapeHtml(b.description)} (${isRo() ? 'Dezinstalat' : 'Uninstalled'})</div>
            </div>
            <div class="row-actions">
              <button class="btn btn-action-small" onclick="executeOptimization('debloat_restore', '${pkg}')">♻️ ${isRo() ? 'Restaurează (Undo)' : 'Restore (Undo)'}</button>
            </div>
          `;
          bloatListEl.appendChild(row);
        });
      }
    }

    // Security & AdGuard DNS Card
    const dnsBadge = document.getElementById('dnsStatusBadge');
    const secList = document.getElementById('securityAuditList');
    if (dnsBadge) {
      if (securityAudit.adguard_active) {
        dnsBadge.className = 'badge success';
        dnsBadge.textContent = isRo() ? '🛡️ AdGuard Activ' : '🛡️ AdGuard Active';
      } else {
        dnsBadge.className = 'badge info';
        dnsBadge.textContent = isRo() ? 'DNS Standard' : 'Standard DNS';
      }
    }
    if (secList) {
      secList.innerHTML = '';
      const sideloaded = securityAudit.sideloaded_apps || [];
      if (sideloaded.length === 0) {
        secList.innerHTML = `<li style="color:#4ade80;">${isRo() ? '✓ Toate aplicațiile provin din magazinul oficial.' : '✓ All user apps originate from official stores.'}</li>`;
      } else {
        sideloaded.forEach(app => {
          const pkg = escapeHtml(app.package);
          const li = document.createElement('li');
          li.innerHTML = `
            <span title="${pkg}">${pkg} <small style="color:#94a3b8;">(${escapeHtml(app.installer)})</small></span>
            <div class="list-item-right">
              <button class="btn-mini" onclick="executeOptimization('restrict_app_background', '${pkg}')">${isRo() ? 'Restricționează' : 'Restrict'}</button>
            </div>
          `;
          secList.appendChild(li);
        });
      }
    }

    // Storage Breakdown & WakeLocks Card
    const stWlList = document.getElementById('storageBreakdownList');
    if (stWlList) {
      stWlList.innerHTML = '';
      const apksCnt = storageBreakdown.leftover_apks_count || 0;
      const thumbMb = storageBreakdown.thumbnails_cache_mb || 0;
      const wlCnt = batteryDrain.active_wakelocks_count || 0;

      const summaryLi = document.createElement('li');
      summaryLi.innerHTML = `
        <span style="color:#93c5fd;">${isRo() ? 'Miniaturi Foto / Kituri APK / WakeLocks:' : 'Thumbnails / Leftover APKs / WakeLocks:'}</span>
        <span class="val-pill">${thumbMb} MB • ${apksCnt} APKs • ${wlCnt} WakeLocks</span>
      `;
      stWlList.appendChild(summaryLi);

      (storageBreakdown.top_folders || []).slice(0, 5).forEach(f => {
        const li = document.createElement('li');
        li.innerHTML = `
          <span>📁 ${escapeHtml(f.path)}</span>
          <span class="val-pill">${f.size_mb} MB</span>
        `;
        stWlList.appendChild(li);
      });
    }

    // 3. UI Fluency & Jank Card
    const jankPct = uiFluency.global_jank_percent || 0;
    const peakRr = uiFluency.peak_refresh_rate || 120;
    const animScale = uiFluency.window_animation_scale !== undefined ? uiFluency.window_animation_scale : 1.0;
    const accServices = sysPressure.accessibility_services || [];

    document.getElementById('uiJankVal').textContent = isRo() ? `${jankPct}% cadre întârziate` : `${jankPct}% janky frames`;
    document.getElementById('uiRefreshVal').textContent = isRo() ? `${peakRr} Hz • Animații ${animScale}x` : `${peakRr} Hz • Animations ${animScale}x`;
    document.getElementById('uiAccessVal').textContent = accServices.length > 0
      ? (isRo() ? `${accServices.length} active (Cauză lag!)` : `${accServices.length} active (Lag cause!)`)
      : (isRo() ? '0 (Curat)' : '0 (Clean)');
    document.getElementById('uiStatusNote').textContent = jankPct >= 10
      ? (isRo() ? 'Sacadare detectată în randarea GPU — apasă pe "Elimină Sacadarea"' : 'GPU frame drops detected — click "Fix UI Stutter"')
      : (animScale <= 0.5
          ? (isRo() ? 'Animații ultra-rapide 0.5x active' : 'Snappy 0.5x animations active')
          : (isRo() ? 'Poți seta animațiile la 0.5x pentru fluiditate sporită' : 'Set animations to 0.5x for snappier response'));

    // 4. Storage
    const storageFill = document.getElementById('storageFill');
    storageFill.style.width = `${storage.percent_used || 0}%`;
    storageFill.className = `meter-fill ${storage.status || ''}`;
    document.getElementById('storageUsedText').textContent = isRo() ? `${storage.used_gb || 0} GB Utilizați` : `${storage.used_gb || 0} GB Used`;
    document.getElementById('storageTotalText').textContent = isRo()
      ? `${storage.free_gb || 0} GB Liberi (${storage.percent_used || 0}%)`
      : `${storage.free_gb || 0} GB Free (${storage.percent_used || 0}%)`;
    document.getElementById('storageStatusText').textContent = `I/O Stall: ${sysPressure.io_stall_percent || 0}% • ${storage.summary || ''}`;

    // 5. Memory RAM
    document.getElementById('ramUsageVal').textContent = `${memory.used_mb || 0} / ${memory.total_mb || 0} MB (${memory.ram_percent_used || 0}%)`;
    document.getElementById('zramUsageVal').textContent = `${memory.swap_used_mb || 0} / ${memory.swap_total_mb || 0} MB (${memory.swap_percent_used || 0}%)`;
    document.getElementById('ramStatusText').textContent = isRo()
      ? `${memory.available_mb || 0} MB liberi • Mem Stall: ${sysPressure.mem_stall_percent || 0}%`
      : `${memory.available_mb || 0} MB available • Mem Stall: ${sysPressure.mem_stall_percent || 0}%`;

    // 6. Thermals & CPU
    document.getElementById('tempVal').textContent = `${thermals.battery_temp_c || 0} °C`;
    document.getElementById('throttleVal').textContent = thermals.thermal_status || 'Normal';
    document.getElementById('uptimeVal').textContent = dev.uptime_str || 'N/A';
    document.getElementById('thermalStatusNote').textContent = thermals.thermal_severity !== 'normal'
      ? (isRo() ? 'Temperatură ridicată — folosește oprirea proceselor din fundal' : 'Elevated temperature — stop background CPU hogs')
      : (isRo() ? 'Temperatură în parametri optimi pentru procesor' : 'Temperature within optimal operating range');

    // 7. ANR & Crashes
    const anrBadge = document.getElementById('anrCountBadge');
    anrBadge.textContent = `${anrs.total_anrs || 0} ANR / ${anrs.total_crashes || 0} Crash`;
    anrBadge.className = `badge ${anrs.status === 'critical' ? 'danger' : (anrs.status === 'warning' ? 'warning' : 'success')}`;

    const anrList = document.getElementById('anrList');
    anrList.innerHTML = '';
    const recentAnrs = anrs.recent_anrs || [];

    if (recentAnrs.length === 0) {
      anrList.innerHTML = isRo()
        ? '<div style="padding:16px; color:#4ade80; text-align:center;">Nu s-au găsit blocaje de tip "Not Responding" recente în jurnalele sistem!</div>'
        : '<div style="padding:16px; color:#4ade80; text-align:center;">No recent "Not Responding" (ANR) freezes or crashes found in the last 24h!</div>';
    } else {
      const btnRepairLbl = isRo() ? '🔧 Repară (Păstrează Date)' : '🔧 Repair (Keep Data)';
      const btnRestrictLbl = isRo() ? '🛑 Restricționează Fundal' : '🛑 Restrict Background';
      const btnResetLbl = isRo() ? '🗑️ Reset Complet' : '🗑️ Full Reset';
      recentAnrs.forEach(ev => {
        const pkg = escapeHtml(ev.package);
        const row = document.createElement('div');
        row.className = 'anr-row';
        row.innerHTML = `
          <div>
            <div class="anr-pkg">${pkg}</div>
            <div class="anr-meta">${escapeHtml(ev.type)} • ${escapeHtml(ev.date)}</div>
            <div class="anr-meta" style="color:#94a3b8; font-size:0.75rem; margin-top:2px;">${escapeHtml(ev.details || '')}</div>
          </div>
          <div class="row-actions">
            <button class="btn btn-action-small" onclick="executeOptimization('deep_repair_app', '${pkg}')">${btnRepairLbl}</button>
            <button class="btn btn-action-small btn-warn-small" onclick="executeOptimization('restrict_app_background', '${pkg}')">${btnRestrictLbl}</button>
            <button class="btn btn-action-small btn-danger-small" onclick="executeOptimization('clear_package_cache', '${pkg}')">${btnResetLbl}</button>
          </div>
        `;
        anrList.appendChild(row);
      });
    }

    // 8. UI Jank / Frame Drop Apps List
    const jankAppsList = document.getElementById('jankAppsList');
    const jankBadge = document.getElementById('jankCountBadge');
    const jankyApps = uiFluency.janky_apps || [];
    jankBadge.textContent = isRo()
      ? `${jankyApps.length} Aplicații Analizate (${jankPct}% Jank Global)`
      : `${jankyApps.length} Apps Sampled (${jankPct}% Global Jank)`;
    jankBadge.className = `badge ${jankPct >= 15 ? 'danger' : (jankPct >= 8 ? 'warning' : 'success')}`;

    jankAppsList.innerHTML = '';
    if (jankyApps.length === 0) {
      jankAppsList.innerHTML = isRo()
        ? '<div style="padding:14px; color:#94a3b8; text-align:center;">Nu există statistici de cadre pierdute momentan (sau tocmai au fost resetate).</div>'
        : '<div style="padding:14px; color:#94a3b8; text-align:center;">No frame drop metrics currently recorded (or counters were just reset).</div>';
    } else {
      const btnSpeedLbl = isRo() ? '⚡ Compilează Speed & Curăță Cache' : '⚡ Speed Compile & Clear Cache';
      jankyApps.forEach(app => {
        const pkg = escapeHtml(app.package);
        const row = document.createElement('div');
        row.className = 'anr-row';
        const meta1 = isRo()
          ? `Cadre sacadate (Jank): <strong>${app.jank_percent}%</strong> (${app.janky_frames} din ${app.total_frames} cadre)`
          : `Janky frames: <strong>${app.jank_percent}%</strong> (${app.janky_frames} of ${app.total_frames} frames)`;
        const meta2 = isRo()
          ? `Timp randare 95th: ${app.p95_ms}ms • 99th: ${app.p99_ms}ms`
          : `Render time 95th: ${app.p95_ms}ms • 99th: ${app.p99_ms}ms`;
        row.innerHTML = `
          <div>
            <div class="anr-pkg" style="color:#93c5fd;">${pkg}</div>
            <div class="anr-meta">${meta1}</div>
            <div class="anr-meta" style="color:#94a3b8; font-size:0.75rem;">${meta2}</div>
          </div>
          <div class="row-actions">
            <button class="btn btn-action-small" onclick="executeOptimization('deep_repair_app', '${pkg}')">${btnSpeedLbl}</button>
          </div>
        `;
        jankAppsList.appendChild(row);
      });
    }

    // 9. Top Lists (RAM & CPU)
    const topRamList = document.getElementById('topRamList');
    topRamList.innerHTML = '';
    const stopLbl = isRo() ? 'Oprește' : 'Force Stop';
    (memory.top_apps || []).forEach(app => {
      const pkg = escapeHtml(app.package);
      const li = document.createElement('li');
      li.innerHTML = `
        <span title="${pkg}">${pkg}</span>
        <div class="list-item-right">
          <span class="val-pill">${app.memory_mb} MB</span>
          <button class="btn-mini" onclick="executeOptimization('force_stop', '${pkg}')">${stopLbl}</button>
        </div>
      `;
      topRamList.appendChild(li);
    });

    const topCpuList = document.getElementById('topCpuList');
    topCpuList.innerHTML = '';
    const restrictLbl = isRo() ? 'Blochează' : 'Restrict';
    (thermals.top_cpu_apps || []).forEach(app => {
      const pkg = escapeHtml(app.package);
      const li = document.createElement('li');
      li.innerHTML = `
        <span title="${pkg}">${pkg}</span>
        <div class="list-item-right">
          <span class="val-pill">${app.cpu_percent}% CPU</span>
          <button class="btn-mini" onclick="executeOptimization('restrict_app_background', '${pkg}')">${restrictLbl}</button>
        </div>
      `;
      topCpuList.appendChild(li);
    });
  }

  function renderJobStatus(job) {
    if (!liveConsoleCard) return;
    liveConsoleCard.classList.remove('hidden');

    if (job.phone_activity) {
      updatePhoneActivityUI(job.phone_activity);
    }

    const pct = job.percent || 0;
    liveProgressBarFill.style.width = `${pct}%`;
    liveStepCounter.textContent = isRo()
      ? `Pasul ${job.step || 0} / ${job.total_steps || 1} (${pct}%)`
      : `Step ${job.step || 0} / ${job.total_steps || 1} (${pct}%)`;
    liveElapsedTimer.textContent = `⏱️ ${job.elapsed_sec || 0}s`;
    liveCurrentTaskBox.textContent = job.current_task || '';

    if (job.running) {
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = isRo() ? '🔄 ÎN CURS DE EXECUȚIE...' : '🔄 RUNNING...';
      liveProgressBarFill.className = 'live-progress-fill running';
      liveFinishBanner.classList.add('hidden');
    } else if (job.completed) {
      if (job.success) {
        liveStatusBadge.className = 'badge success';
        liveStatusBadge.textContent = isRo() ? '✅ FINALIZAT CU SUCCES (100%)' : '✅ COMPLETED SUCCESSFULLY (100%)';
        liveProgressBarFill.className = 'live-progress-fill done';
      } else {
        liveStatusBadge.className = 'badge danger';
        liveStatusBadge.textContent = isRo() ? '⚠️ EROARE LA EXECUȚIE' : '⚠️ EXECUTION ERROR';
        liveProgressBarFill.className = 'live-progress-fill error';
      }
      liveFinishBanner.classList.remove('hidden');
      liveFinishText.textContent = job.result_message || (isRo() ? 'Operațiunea s-a încheiat.' : 'Operation finished.');
    }

    const logs = job.logs || [];
    liveLogContainer.innerHTML = '';
    logs.forEach(line => {
      const div = document.createElement('div');
      div.className = 'log-line';
      if (line.includes('✓') || line.includes('✅') || line.includes('🎉') || line.includes('♻️') || line.includes('🛡️')) {
        div.classList.add('log-success');
      } else if (line.includes('⏳')) {
        div.classList.add('log-working');
      } else if (line.includes('❌')) {
        div.classList.add('log-error');
      }
      div.textContent = line;
      liveLogContainer.appendChild(div);
    });
    liveLogContainer.scrollTop = liveLogContainer.scrollHeight;
  }

  function startJobPolling() {
    if (jobPollInterval) clearInterval(jobPollInterval);
    jobPollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/job-status?lang=${currentLang}`);
        if (!res.ok) return;
        const job = await res.json();
        renderJobStatus(job);
        if (!job.running && job.completed) {
          clearInterval(jobPollInterval);
          jobPollInterval = null;
          showToast('✅ ' + (job.result_message || (isRo() ? 'Reparația s-a finalizat!' : 'Repair completed!')), 6000);
        }
      } catch (e) {
        console.error('Job poll error:', e);
      }
    }, 700);
  }

  window.loadInstalledPackages = async function(silent = false) {
    const datalist = document.getElementById('installedPackagesList');
    if (!datalist) return;
    try {
      const qs = activeDevice ? `?serial=${encodeURIComponent(activeDevice.serial)}&lang=${currentLang}` : `?lang=${currentLang}`;
      const res = await fetch(`/api/packages${qs}`);
      if (!res.ok) return;
      const data = await res.json();
      const pkgs = data.packages || [];
      datalist.innerHTML = '';
      pkgs.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        datalist.appendChild(opt);
      });
      if (!silent) {
        showToast(isRo() ? `✅ S-au încărcat ${pkgs.length} pachete instalate!` : `✅ Loaded ${pkgs.length} installed packages!`);
      }
    } catch (e) {
      console.error('Error loading packages:', e);
    }
  };

  window.runCustomAppAction = function(action) {
    const input = document.getElementById('customPkgInput');
    const pkg = (input?.value || '').trim();
    if (!pkg || !pkg.includes('.')) {
      alert(
        isRo()
          ? 'Te rugăm să selectezi sau să introduci un nume valid de pachet (ex: com.whatsapp, com.stremio.one)!'
          : 'Please select or enter a valid package name (e.g. com.whatsapp, com.stremio.one)!'
      );
      return;
    }
    window.executeOptimization(action, pkg);
  };

  window.executeOptimization = async function(action, pkg = null) {
    if (action === 'reboot') {
      if (!confirm(isRo() ? 'Ești sigur că vrei să repornești dispozitivul acum?' : 'Are you sure you want to reboot the device now?')) return;
    } else if (action === 'clear_package_cache') {
      const warnMsg = isRo()
        ? `ATENȚIE: 'Reset Complet' va șterge toate datele și contul din aplicația ${pkg}. Dacă vrei să păstrezi contul, apasă Anulare și folosește '🔧 Repară (Păstrează Date)'. Continui?`
        : `WARNING: 'Full Reset' will wipe all user data and login state for ${pkg}. If you want to keep your account, cancel and click '🔧 Repair (Keep Data)'. Proceed?`;
      if (!confirm(warnMsg)) return;
    }

    if (liveConsoleCard) {
      liveConsoleCard.classList.remove('hidden');
      liveFinishBanner.classList.add('hidden');
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = isRo() ? '🔄 PORNIRE...' : '🔄 STARTING...';
      liveProgressBarFill.style.width = '5%';
      liveCurrentTaskBox.textContent = isRo() ? 'Se trimite comanda către dispozitiv prin ADB...' : 'Sending ADB command to device...';
      liveConsoleCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    try {
      const res = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          package: pkg,
          serial: activeDevice ? activeDevice.serial : null,
          lang: currentLang
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Error');
      startJobPolling();
    } catch (err) {
      alert((isRo() ? 'Eroare la optimizare: ' : 'Optimization error: ') + err.message);
    }
  };

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  checkDeviceStatus();
  statusPollInterval = setInterval(checkDeviceStatus, 3000);
});
