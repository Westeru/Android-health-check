document.addEventListener('DOMContentLoaded', () => {
  let activeDevice = null;
  let selectedSerial = null;
  let statusPollInterval = null;
  let jobPollInterval = null;
  let currentLang = localStorage.getItem('ahd_lang') || 'en';
  let lastScanReport = null;

  const I18N = {
    en: {
      header_subtitle: 'Deep diagnostics & repair for UI Jank, App Freezes (ANRs), System Databases & ART Compilation (USB / Wi-Fi)',
      btn_wireless_header: '📶 Wireless ADB (No USB)',
      btn_guide: 'ADB Setup Guide (USB / Wi-Fi)',
      lbl_active_device: 'Active device:',
      btn_wireless_mode: '📶 Wireless Wi-Fi Mode',
      btn_super_boost_top: '⚡ 1-Click Super Boost',
      btn_scan_phone: 'Scan Phone',
      wireless_title: '📶 Wireless ADB Connection (Cable-Free / Broken USB Port)',
      wireless_subtitle: 'Connect any Android 11+ phone directly over your local Wi-Fi network',
      btn_mdns_discover: '🔍 Auto-Discover Phone on Wi-Fi',
      btn_hide: '✕ Hide',
      wireless_steps_html: '<strong>How to enable on phone (without cable):</strong> 1. Connect phone to the same Wi-Fi as this PC. &bull; 2. Go to <em>Settings &rarr; Developer options &rarr; <strong>Wireless debugging</strong></em> and turn it ON. &bull; 3. Tap on the <strong>Wireless debugging</strong> text to see your IP address and pairing code option.',
      pair_step_title: '1️⃣ First-Time Setup: Pair with 6-Digit Code',
      pair_step_desc: 'On your phone, tap "Pair device with pairing code" and enter the details shown in the popup:',
      lbl_pair_ip: 'Pairing IP & Port (from phone popup):',
      lbl_pair_code: 'Wi-Fi Pairing Code (6 digits):',
      lbl_pair_conn_port: 'Connection Port (optional):',
      btn_pair_submit: '🔗 Pair & Connect Phone',
      conn_step_title: '2️⃣ Direct Connect (Already Paired)',
      conn_step_desc: 'If this PC is already paired with your phone, enter the IP address & Port shown on the main Wireless debugging screen:',
      lbl_conn_ip: 'Connection IP & Port (from Wireless debugging screen):',
      btn_conn_submit: '📶 Connect via Wi-Fi',
      btn_disconnect_wifi: '🔌 Disconnect Wi-Fi',
      live_console_title: 'Live Repair Execution Console',
      btn_close: '✕ Close',
      btn_rescan_now: '🔍 Rescan Phone Now',
      btn_reboot_zram: '🔄 Reboot Phone (Recommended to flush ZRAM)',
      scan_progress_label: 'Analyzing GPU frame drops (UI Jank), ANR/crash logs, system SQLite databases, ZRAM swap, and storage...',
      toolbar_title: '🛠️ Quick Repair & Optimization Bar (Universal Android)',
      toolbar_hint: 'Direct non-destructive ADB actions to eliminate UI stutter, unlock system databases, and free memory',
      tb_fix_all: '⚡ Fix All (Anti-Lag & Anti-Freeze)',
      tb_fix_db: '📇 Repair System Databases (Contacts / MediaStore / Sync)',
      tb_fix_zram: '🧠 Relieve ZRAM & Stop Parasitic Daemons (AI / Telemetry)',
      tb_fix_stutter: '🚀 Fix UI Stutter (120Hz + 0.5x Animations + Launcher/WebView)',
      tb_free_ram: '🧹 Free RAM & Stop Background Hogs',
      tb_fstrim: '💾 Flash TRIM (fstrim) & Cache Clean',
      tb_restore_anim: '🔄 Default Animations (1.0x)',
      issues_title: 'Identified root causes for stutter & freezes:',
      recom_title: 'Tailored Repair & Action Plan',
      custom_app_title: 'Universal Installed App Explorer & Repair',
      btn_load_packages: '🔄 Load Installed Apps',
      custom_app_desc: 'Have a specific app that loads slowly, freezes, or drains battery in the background? Select or type its package name below to repair it:',
      custom_pkg_placeholder: 'Search or type package name (e.g. com.whatsapp, com.instagram.android)...',
      btn_custom_repair: '🔧 Repair & Speed Compile (Keep Data)',
      btn_custom_restrict: '🛑 Restrict Background',
      btn_custom_reset: '🗑️ Full Data Reset',
      card_ui_title: 'UI Fluency & Display',
      lbl_jank_frames: 'Dropped Frames (Jank):',
      lbl_refresh_anim: 'Refresh Rate / Animations:',
      lbl_access_hooks: 'Accessibility Hooks:',
      card_storage_title: 'Internal UFS Storage',
      card_ram_title: 'RAM & ZRAM Swap',
      lbl_ram_used: 'Used RAM:',
      card_thermal_title: 'Thermals & Processor',
      lbl_bat_temp: 'Battery Temperature:',
      lbl_throttle: 'Throttling Status:',
      lbl_uptime: 'System Uptime:',
      anr_section_title: 'Freezing & Crashing Apps (ANR / Crash in the Last 24h)',
      anr_section_desc: 'Use 🔧 Repair (Keep Data) to clear only corrupted cache and AOT-compile the app in native speed mode without wiping your account!',
      jank_section_title: 'Apps with UI Stutter (GPU Frame Drops)',
      jank_section_desc: 'These packages missed GPU frame rendering deadlines (>8.3ms at 120Hz / >16.6ms at 60Hz), causing visible scrolling stutter:',
      top_ram_title: 'Top RAM Consumers (Quick Force-Stop)',
      top_cpu_title: 'Top Active CPU Processes',
      modal_guide_title: 'How to Enable USB or Wireless Debugging on Android',
      btn_got_it: 'Got it',
      modal_steps_html: `
        <li><strong>Open Settings</strong> on your Android phone (Samsung, Pixel, Xiaomi, OnePlus, Motorola, etc.).</li>
        <li>Go to <strong>About phone</strong> &rarr; find <strong>Build number</strong> (or MIUI / OS Version) and tap it rapidly <strong>7 times</strong> until you see <em>"You are now a developer!"</em>.</li>
        <li>Go to <strong>Settings &rarr; System / Additional settings &rarr; Developer options</strong>.</li>
        <li><strong>For USB Cable:</strong> Enable <strong>USB debugging</strong>, plug in the cable, and tap <strong>Allow</strong> on the phone screen.</li>
        <li><strong>For Wi-Fi (Cable-Free):</strong> Enable <strong>Wireless debugging</strong>, tap on its text to open the pairing screen, and use the <em>📶 Wireless ADB</em> panel in this app.</li>
      `
    },
    ro: {
      header_subtitle: 'Diagnostic & reparare sacadare (UI Jank), aplicații blocate (ANR), baze de date sistem & compilare ART (USB / Wi-Fi)',
      btn_wireless_header: '📶 Conectare Wireless (Fără USB)',
      btn_guide: 'Ghid Activare ADB (USB / Wi-Fi)',
      lbl_active_device: 'Dispozitiv activ:',
      btn_wireless_mode: '📶 Mod Wireless Wi-Fi',
      btn_super_boost_top: '⚡ Super-Optimizare 1-Click',
      btn_scan_phone: 'Scanează Telefonul',
      wireless_title: '📶 Conectare Wireless ADB (Pentru telefoane fără cablu sau cu port USB defect)',
      wireless_subtitle: 'Conectează orice telefon cu Android 11+ direct prin rețeaua Wi-Fi locală',
      btn_mdns_discover: '🔍 Caută automat telefonul în Wi-Fi',
      btn_hide: '✕ Ascunde',
      wireless_steps_html: '<strong>Cum activezi pe telefon (fără cablu):</strong> 1. Conectează telefonul la același Wi-Fi cu PC-ul. &bull; 2. Mergi în <em>Setări &rarr; Opțiuni dezvoltator &rarr; <strong>Depanare wireless (Wireless debugging)</strong></em> și pornește-o. &bull; 3. Apasă pe textul <strong>Depanare wireless</strong> pentru a vedea IP-ul și opțiunea de asociere cu cod.',
      pair_step_title: '1️⃣ Prima Conectare: Asociere cu Cod (6 cifre)',
      pair_step_desc: 'Pe telefon, apasă pe „Asociați dispozitivul cu un cod de asociere” și introdu datele afișate:',
      lbl_pair_ip: 'IP și Port de Asociere (din fereastra pop-up):',
      lbl_pair_code: 'Cod Asociere (6 cifre):',
      lbl_pair_conn_port: 'Port Conectare (opțional):',
      btn_pair_submit: '🔗 Asociază și Conectează Telefonul',
      conn_step_title: '2️⃣ Conectare Directă (Dacă a fost deja asociat)',
      conn_step_desc: 'Dacă telefonul a mai fost asociat cu acest PC, introdu Adresa IP și Portul afișate pe pagina principală Depanare wireless:',
      lbl_conn_ip: 'IP și Port Conectare (de pe ecranul Depanare wireless):',
      btn_conn_submit: '📶 Conectează prin Wi-Fi',
      btn_disconnect_wifi: '🔌 Deconectează Wi-Fi',
      live_console_title: 'Consolă Execuție Reparații Live',
      btn_close: '✕ Închide',
      btn_rescan_now: '🔍 Re-scanează Telefonul Acum',
      btn_reboot_zram: '🔄 Restart Telefon (Recomandat pt. golirea ZRAM)',
      scan_progress_label: 'Se analizează cadrele pierdute (UI Jank), jurnalele ANR, bazele de date de sistem, memoria ZRAM și stocarea...',
      toolbar_title: '🛠️ Panou de Intervenție Rapidă (Universal Android)',
      toolbar_hint: 'Acțiuni directe prin ADB pentru eliminarea sacadării, deblocarea bazelor de date și optimizarea memoriei',
      tb_fix_all: '⚡ Repară Tot (Anti-Lag & Anti-Freeze)',
      tb_fix_db: '📇 Repară Baze de Date Sistem (Contacte / MediaStore / Sync)',
      tb_fix_zram: '🧠 Deblocare ZRAM & Stop Servicii Parazite (AI / Telemetrie)',
      tb_fix_stutter: '🚀 Elimină Sacadarea (120Hz + Animații 0.5x + Launcher/WebView)',
      tb_free_ram: '🧹 Eliberează RAM & Oprește Fundalul',
      tb_fstrim: '💾 Trim Stocare Flash & Cache',
      tb_restore_anim: '🔄 Animații 1.0x (Standard)',
      issues_title: 'Cauzele identificate pentru sacadare și blocaje:',
      recom_title: 'Plan de Reparare Personalizat',
      custom_app_title: 'Reparare & Optimizare pentru Orice Aplicație Instalată',
      btn_load_packages: '🔄 Încarcă Lista Aplicațiilor',
      custom_app_desc: 'Ai o aplicație care se deschide greu, îngheață sau consumă bateria în fundal? Selecteaz-o sau scrie numele pachetului mai jos pentru a o repara:',
      custom_pkg_placeholder: 'Caută sau scrie un pachet (ex: com.whatsapp, com.instagram.android)...',
      btn_custom_repair: '🔧 Repară & Compilează Speed (Fără pierdere date)',
      btn_custom_restrict: '🛑 Restricționează Fundal',
      btn_custom_reset: '🗑️ Reset Bază Date (Complet)',
      card_ui_title: 'Fluență UI & Ecran',
      lbl_jank_frames: 'Cadre Pierdute (Jank):',
      lbl_refresh_anim: 'Rată Refresh / Animații:',
      lbl_access_hooks: 'Hook-uri Accesibilitate:',
      card_storage_title: 'Stocare Internă UFS',
      card_ram_title: 'Memorie RAM & ZRAM',
      lbl_ram_used: 'RAM Utilizat:',
      card_thermal_title: 'Termice & Procesor',
      lbl_bat_temp: 'Temperatură Baterie:',
      lbl_throttle: 'Stare Throttling:',
      lbl_uptime: 'Timp fără Restart:',
      anr_section_title: 'Aplicații care se Blochează (ANR / Crash / Înghețare în ultimele 24h)',
      anr_section_desc: 'Folosește butonul 🔧 Repară (Păstrează Date) pentru a curăța doar cache-ul corupt și a recompila nativ aplicația în mod speed (fără să îți șteargă contul!).',
      jank_section_title: 'Aplicații cu Mișcare Sacadată (Frame Drops / Lag Grafic)',
      jank_section_desc: 'Aceste aplicații au întârziat randarea cadrelor pe ecran (peste 8.3ms / 16.6ms), provocând senzația de agățare sau scroll sacadat:',
      top_ram_title: 'Top Consumatori Memorie RAM (Cu oprire rapidă)',
      top_cpu_title: 'Top Consumatori CPU Recenți (Procese active)',
      modal_guide_title: 'Cum activezi Depanarea USB sau Wireless pe Android',
      btn_got_it: 'Am înțeles',
      modal_steps_html: `
        <li><strong>Deschide Setările</strong> pe telefonul Android (Samsung, Pixel, Xiaomi, OnePlus, Motorola etc.).</li>
        <li>Mergi la <strong>Despre telefon</strong> (About phone) &rarr; găsește <strong>Număr versiune</strong> (Build number) și atinge-l rapid de <strong>7 ori</strong> până apare mesajul <em>„Acum ești un dezvoltator!”</em>.</li>
        <li>Intră în <strong>Setări &rarr; Sistem / Setări suplimentare &rarr; Opțiuni pentru dezvoltatori</strong>.</li>
        <li><strong>Pentru Cablu USB:</strong> Activează <strong>Depanare USB</strong>, conectează cablul și apasă pe <strong>Permiteți</strong> (Allow) pe ecranul telefonului.</li>
        <li><strong>Pentru Wi-Fi (Fără Cablu):</strong> Activează <strong>Depanare wireless</strong>, apasă pe textul ei și folosește panoul <em>📶 Conectare Wireless</em> din aplicație.</li>
      `
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
    const modalSteps = document.getElementById('modalStepsList');
    if (modalSteps && dict.modal_steps_html) {
      modalSteps.innerHTML = dict.modal_steps_html;
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
      ? '<span style="color:#93c5fd;">🔍 Se scanează rețeaua Wi-Fi pentru telefoane cu Depanare Wireless activă...</span>'
      : '<span style="color:#93c5fd;">🔍 Scanning Wi-Fi network for phones with Wireless Debugging enabled...</span>';
    try {
      const res = await fetch(`/api/wireless/discover?lang=${currentLang}`);
      const data = await res.json();
      const pairs = data.pairing_services || [];
      const connects = data.connect_services || [];

      if (pairs.length === 0 && connects.length === 0) {
        mdnsDiscoveryBox.innerHTML = isRo()
          ? '<span style="color:#94a3b8;">Niciun telefon detectat automat prin mDNS încă. Deschide meniul <strong>Depanare wireless</strong> pe telefon sau introdu IP-ul și portul manual mai jos.</span>'
          : '<span style="color:#94a3b8;">No phone auto-detected via mDNS yet. Open the <strong>Wireless debugging</strong> menu on your phone or enter the IP and port manually below.</span>';
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
        const lbl = isRo() ? '📶 Detectat pentru Conectare Wi-Fi:' : '📶 Detected for Wi-Fi Connection:';
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
        ? '<span style="color:#f87171;">Eroare la căutarea mDNS. Poți introduce IP-ul și portul manual mai jos.</span>'
        : '<span style="color:#f87171;">mDNS discovery error. You can enter the IP and port manually below.</span>';
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
          ? 'Introdu Adresa IP și Portul de pe pagina Depanare wireless (ex: 192.168.1.105:41555).'
          : 'Enter the IP address and Port shown on the Wireless debugging screen (e.g. 192.168.1.105:41555).',
        true
      );
      return;
    }

    showWirelessMessage(isRo() ? '⏳ Se conectează la telefon prin Wi-Fi...' : '⏳ Connecting to phone via Wi-Fi...');
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
        ? `⚙️ Telefonul lucrează acum: ${phoneActivity.summary}`
        : `⚙️ Phone busy: ${phoneActivity.summary}`;
    } else {
      phoneLiveActivityBadge.className = 'phone-activity-pill activity-idle';
      phoneLiveActivityDot.className = 'activity-dot idle';
      phoneLiveActivityText.textContent = isRo()
        ? '🟢 Stare procese telefon: În repaus (toate optimizările din fundal s-au terminat)'
        : '🟢 Phone background status: Idle (all background tasks completed)';
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
        connStatusTitle.textContent = isRo() ? 'Niciun telefon conectat (USB sau Wi-Fi)' : 'No Android device connected (USB or Wi-Fi)';
        connStatusDesc.textContent = isRo()
          ? 'Conectează telefonul prin cablu USB sau apasă pe „📶 Mod Wireless Wi-Fi” pentru conectare fără cablu.'
          : 'Connect your phone via USB cable or click "📶 Wireless Wi-Fi Mode" for cable-free connection.';
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
        const connIcon = chosenDevice.is_wireless ? '📶 Wi-Fi Wireless' : (isRo() ? '🔌 Cablu USB' : '🔌 USB Cable');
        connectionCard.className = 'card connection-card state-connected';
        connStatusTitle.textContent = isRo()
          ? `Conectat (${connIcon}): ${chosenDevice.model} [${chosenDevice.serial}]`
          : `Connected (${connIcon}): ${chosenDevice.model} [${chosenDevice.serial}]`;
        connStatusDesc.textContent = isRo()
          ? 'Telefonul este autorizat și gata pentru scanare sau optimizare rapidă.'
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
          ? `Dispozitiv detectat (${unauthorizedDevice.model}) - Necesită autorizare`
          : `Device detected (${unauthorizedDevice.model}) - Authorization required`;
        connStatusDesc.textContent = isRo()
          ? 'Deblochează ecranul telefonului și apasă pe "Permiteți depanarea USB" (Allow).'
          : 'Unlock your phone screen and tap "Allow USB/Wireless debugging".';
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
      alert((isRo() ? 'Eroare la scanarea telefonului: ' : 'Error scanning phone: ') + err.message);
    } finally {
      scanBtn.disabled = false;
      scanProgressBar.classList.add('hidden');
    }
  }

  scanBtn.addEventListener('click', triggerScan);

  window.triggerRescanFromConsole = function() {
    triggerScan();
  };

  function renderReport(report) {
    resultsArea.classList.remove('hidden');

    const evalData = report.health_evaluation || {};
    const dev = report.device || {};
    const storage = report.storage || {};
    const memory = report.memory || {};
    const anrs = report.anrs_and_crashes || {};
    const thermals = report.thermals_and_cpu || {};
    const uiFluency = report.ui_fluency || {};
    const sysPressure = report.system_pressure || {};

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

    // 2. Recommendations
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
      'reboot': { label: '🔄 Restart Telefon', cls: 'btn-action-small' }
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
      'reboot': { label: '🔄 Reboot Phone', cls: 'btn-action-small' }
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
    document.getElementById('thermalStatusNote').textContent = thermals.battery_temp_c >= 39
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
          ? `Timp randare 95th: ${app.p95_ms}ms • 99th: ${app.p99_ms}ms (Optim sub 8ms la 120Hz)`
          : `Render time 95th: ${app.p95_ms}ms • 99th: ${app.p99_ms}ms (Optimal <8ms at 120Hz)`;
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
      if (line.includes('✓') || line.includes('✅') || line.includes('🎉')) {
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
          ? 'Te rugăm să selectezi sau să introduci un nume valid de pachet (ex: com.whatsapp, com.instagram.android)!'
          : 'Please select or enter a valid package name (e.g. com.whatsapp, com.instagram.android)!'
      );
      return;
    }
    window.executeOptimization(action, pkg);
  };

  window.executeOptimization = async function(action, pkg = null) {
    if (action === 'reboot') {
      if (!confirm(isRo() ? 'Ești sigur că vrei să repornești telefonul acum?' : 'Are you sure you want to reboot the phone now?')) return;
    } else if (action === 'clear_package_cache') {
      const warnMsg = isRo()
        ? `ATENȚIE: 'Reset Complet' va șterge toate datele și contul din aplicația ${pkg} (ca la reinstalare). Dacă vrei să păstrezi contul, apasă Anulare și folosește '🔧 Repară (Păstrează Date)'. Continui cu Reset Complet?`
        : `WARNING: 'Full Reset' will wipe all user data and login state for ${pkg}. If you want to keep your account and only fix freezes, cancel and click '🔧 Repair (Keep Data)'. Proceed with Full Reset?`;
      if (!confirm(warnMsg)) return;
    } else if (action === 'disable_accessibility') {
      if (!confirm(isRo() ? 'Dezactivezi serviciile de accesibilitate active pentru a elimina lag-ul la atingere și scroll?' : 'Disable active accessibility services to eliminate touch and scrolling stutter?')) return;
    }

    if (liveConsoleCard) {
      liveConsoleCard.classList.remove('hidden');
      liveFinishBanner.classList.add('hidden');
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = isRo() ? '🔄 PORNIRE...' : '🔄 STARTING...';
      liveProgressBarFill.style.width = '5%';
      liveCurrentTaskBox.textContent = isRo() ? 'Se trimite comanda către telefon prin ADB...' : 'Sending ADB command to device...';
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
