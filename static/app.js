document.addEventListener('DOMContentLoaded', () => {
  let activeDevice = null;
  let selectedSerial = null;
  let statusPollInterval = null;
  let jobPollInterval = null;

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
  const liveConsoleTitle = document.getElementById('liveConsoleTitle');
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

  // Event Listeners
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
    mdnsDiscoveryBox.innerHTML = '<span style="color:#93c5fd;">🔍 Se scanează rețeaua Wi-Fi pentru telefoane cu Depanare Wireless activă...</span>';
    try {
      const res = await fetch('/api/wireless/discover');
      const data = await res.json();
      const pairs = data.pairing_services || [];
      const connects = data.connect_services || [];

      if (pairs.length === 0 && connects.length === 0) {
        mdnsDiscoveryBox.innerHTML = '<span style="color:#94a3b8;">Niciun telefon detectat automat prin mDNS încă. Deschide meniul <strong>Depanare wireless</strong> pe telefon sau introdu IP-ul și portul manual mai jos.</span>';
        return;
      }

      let html = '<div style="display:flex; flex-direction:column; gap:8px;">';
      pairs.forEach(p => {
        html += `<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="color:#fde047;">🔑 Detectat în mod Asociere (Pair): <strong>${escapeHtml(p.address)}</strong></span>
          <button class="btn btn-action-small" onclick="document.getElementById('pairAddrInput').value='${escapeHtml(p.address)}'; document.getElementById('pairCodeInput').focus();">Completează IP:Port Asociere</button>
        </div>`;
        const pairInput = document.getElementById('pairAddrInput');
        if (pairInput && !pairInput.value) pairInput.value = p.address;
      });

      connects.forEach(c => {
        html += `<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="color:#4ade80;">📶 Detectat pentru Conectare Wi-Fi: <strong>${escapeHtml(c.address)}</strong></span>
          <button class="btn btn-action-small" onclick="document.getElementById('connectAddrInput').value='${escapeHtml(c.address)}'; window.submitWirelessConnect();">Conectează cu 1-Clic</button>
        </div>`;
        const connInput = document.getElementById('connectAddrInput');
        if (connInput && !connInput.value) connInput.value = c.address;
        const pairConnPort = document.getElementById('pairConnectPortInput');
        if (pairConnPort && !pairConnPort.value) pairConnPort.value = c.port;
      });
      html += '</div>';
      mdnsDiscoveryBox.innerHTML = html;
    } catch (e) {
      mdnsDiscoveryBox.innerHTML = '<span style="color:#f87171;">Eroare la căutarea mDNS. Poți introduce IP-ul și portul manual mai jos.</span>';
    }
  };

  window.submitWirelessPair = async function() {
    const pairAddr = (document.getElementById('pairAddrInput')?.value || '').trim();
    const pairCode = (document.getElementById('pairCodeInput')?.value || '').trim();
    const connPort = (document.getElementById('pairConnectPortInput')?.value || '').trim();

    if (!pairAddr || !pairCode) {
      showWirelessMessage('Te rugăm să introduci atât IP:Port de asociere, cât și codul din 6 cifre afișat pe telefon!', true);
      return;
    }

    showWirelessMessage('⏳ Se asociază cu telefonul prin Wi-Fi... Așteaptă câteva secunde.');
    try {
      const res = await fetch('/api/wireless/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pairing_addr: pairAddr,
          pairing_code: pairCode,
          connect_addr: connPort || null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Eroare la asociere');

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
      showWirelessMessage('Introdu Adresa IP și Portul de pe pagina Depanare wireless (ex: 192.168.1.105:41555).', true);
      return;
    }

    showWirelessMessage('⏳ Se conectează la telefon prin Wi-Fi...');
    try {
      const res = await fetch('/api/wireless/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connect_addr: connAddr })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Eroare la conectare');

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
        body: JSON.stringify({})
      });
      const data = await res.json();
      showWirelessMessage(data.message || 'Deconectat.', false);
      await checkDeviceStatus();
    } catch (err) {
      showWirelessMessage('Eroare la deconectare: ' + err.message, true);
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
      phoneLiveActivityText.textContent = `⚙️ Telefonul lucrează acum: ${phoneActivity.summary}`;
    } else {
      phoneLiveActivityBadge.className = 'phone-activity-pill activity-idle';
      phoneLiveActivityDot.className = 'activity-dot idle';
      phoneLiveActivityText.textContent = '🟢 Stare procese telefon: În repaus (toate optimizările din fundal s-au terminat)';
    }
  }

  // Poll device connection status
  async function checkDeviceStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();

      if (!data.adb_available) {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = 'ADB nu este instalat sau găsit';
        connStatusDesc.textContent = 'Verifică dacă Android Platform Tools este instalat.';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
        return;
      }

      if (!data.devices || data.devices.length === 0) {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = 'Niciun telefon conectat (USB sau Wi-Fi)';
        connStatusDesc.textContent = 'Conectează telefonul prin cablu USB sau apasă pe „📶 Mod Wireless Wi-Fi” pentru conectare fără cablu.';
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
        // Populate selector if more than 1 authorized device
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
        const connIcon = chosenDevice.is_wireless ? '📶 Wi-Fi Wireless' : '🔌 Cablu USB';
        connectionCard.className = 'card connection-card state-connected';
        connStatusTitle.textContent = `Conectat (${connIcon}): ${chosenDevice.model} [${chosenDevice.serial}]`;
        connStatusDesc.textContent = 'Telefonul este autorizat și gata pentru scanare sau optimizare rapidă.';
        scanBtn.disabled = false;
        if (superBoostTopBtn) superBoostTopBtn.disabled = false;
        updatePhoneActivityUI(data.phone_activity);

        if (data.job_running && !jobPollInterval) {
          startJobPolling();
        }
      } else if (unauthorizedDevice) {
        activeDevice = unauthorizedDevice;
        connectionCard.className = 'card connection-card state-unauthorized';
        connStatusTitle.textContent = `Dispozitiv detectat (${unauthorizedDevice.model}) - Necesită autorizare`;
        connStatusDesc.textContent = 'Privește ecranul telefonului Pixel și apasă pe "Permiteți depanarea USB" (Allow).';
        if (phoneLiveActivityBadge) phoneLiveActivityBadge.classList.add('hidden');
        scanBtn.disabled = true;
        if (superBoostTopBtn) superBoostTopBtn.disabled = true;
      } else {
        connectionCard.className = 'card connection-card state-disconnected';
        connStatusTitle.textContent = 'Dispozitiv în stare necunoscută/offline';
        connStatusDesc.textContent = 'Reconectează cablul USB.';
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
        body: JSON.stringify({ serial: activeDevice ? activeDevice.serial : null })
      });

      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try {
          const errData = JSON.parse(text);
          detail = errData.detail || text;
        } catch (_) {}
        throw new Error(detail || 'Eroare la scanare');
      }

      const report = await res.json();
      renderReport(report);
      showToast('Scanare profundă finalizată! Rezultatele au fost actualizate.');
    } catch (err) {
      alert('Eroare la scanarea telefonului: ' + err.message);
    } finally {
      scanBtn.disabled = false;
      scanProgressBar.classList.add('hidden');
    }
  }

  scanBtn.addEventListener('click', triggerScan);

  window.triggerRescanFromConsole = function() {
    triggerScan();
  };

  // Render scan report to UI
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

    // 1. Score & verdict
    const scoreVal = evalData.score || 0;
    const scoreEl = document.getElementById('scoreValue');
    scoreEl.textContent = scoreVal;

    const badgeEl = document.getElementById('scoreBadge');
    badgeEl.className = `badge ${evalData.badge_class || 'info'}`;
    badgeEl.textContent = evalData.verdict || 'Rezultat';

    document.getElementById('scoreTitle').textContent = `${dev.brand ? dev.brand + ' ' : ''}${dev.model || 'Android'} - ${evalData.verdict}`;
    document.getElementById('scoreSummary').textContent = `Android ${dev.android_version || ''} | SoC: ${dev.soc || 'ARM64'} | Patch: ${dev.security_patch || 'N/A'} | Uptime: ${dev.uptime_str || 'N/A'}`;
    const socTitle = document.getElementById('socCardTitle');
    if (socTitle) socTitle.textContent = `Termice & Procesor (${dev.soc || 'SoC'})`;
    window.loadInstalledPackages(true);

    // Issues list
    const issuesList = document.getElementById('issuesList');
    issuesList.innerHTML = '';
    const issues = evalData.issues || [];
    if (issues.length === 0) {
      issuesList.innerHTML = '<li style="color:#4ade80;">Nu au fost detectate probleme critice de performanță!</li>';
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

    const actionButtonMap = {
      'deep_boost_all': { label: '⚡ Super-Optimizare Completă', cls: 'btn-accent' },
      'fix_contacts_acore': { label: '📇 Repară Baze Date Sistem (Contacte/Media)', cls: 'btn-action-small' },
      'debloat_pixel8': { label: '🧠 Deblocare ZRAM & Stop Servicii Parazite', cls: 'btn-action-small' },
      'fix_ui_stutter': { label: '🚀 Elimină Sacadarea (120Hz + 0.5x)', cls: 'btn-action-small' },
      'disable_accessibility': { label: '🛡️ Dezactivează Accesibilitate', cls: 'btn-action-small' },
      'deep_repair_app': { label: '🔧 Repară Aplicația (Păstrează Date)', cls: 'btn-action-small' },
      'storage_clean': { label: '💾 Trim Flash & Curățare Cache', cls: 'btn-action-small' },
      'optimize_ram': { label: '🧹 Eliberează RAM & Fundal', cls: 'btn-action-small' },
      'cool_down': { label: '❄️ Oprește Consumatori CPU', cls: 'btn-action-small' },
      'art_optimize': { label: '⚙️ Compilare ART Speed', cls: 'btn-action-small' },
      'clear_package_cache': { label: '🗑️ Reset Complet Aplicație', cls: 'btn-action-small' },
      'reboot': { label: '🔄 Restart Telefon', cls: 'btn-action-small' }
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

    document.getElementById('uiJankVal').textContent = `${jankPct}% cadre întârziate`;
    document.getElementById('uiRefreshVal').textContent = `${peakRr} Hz • Animații ${animScale}x`;
    document.getElementById('uiAccessVal').textContent = accServices.length > 0 ? `${accServices.length} active (Cauză lag!)` : '0 (Curat)';
    document.getElementById('uiStatusNote').textContent = jankPct >= 10
      ? 'Sacadare detectată în randarea GPU — apasă pe "Elimină Sacadarea"'
      : (animScale <= 0.5 ? 'Animații ultra-rapide 0.5x active' : 'Poți seta animațiile la 0.5x pentru fluiditate sporită');

    // 4. Storage
    const storageFill = document.getElementById('storageFill');
    storageFill.style.width = `${storage.percent_used || 0}%`;
    storageFill.className = `meter-fill ${storage.status || ''}`;
    document.getElementById('storageUsedText').textContent = `${storage.used_gb || 0} GB Utilizați`;
    document.getElementById('storageTotalText').textContent = `${storage.free_gb || 0} GB Liberi (${storage.percent_used || 0}%)`;
    document.getElementById('storageStatusText').textContent = `I/O Stall: ${sysPressure.io_stall_percent || 0}% • ${storage.summary || ''}`;

    // 5. Memory RAM
    document.getElementById('ramUsageVal').textContent = `${memory.used_mb || 0} / ${memory.total_mb || 0} MB (${memory.ram_percent_used || 0}%)`;
    document.getElementById('zramUsageVal').textContent = `${memory.swap_used_mb || 0} / ${memory.swap_total_mb || 0} MB (${memory.swap_percent_used || 0}%)`;
    document.getElementById('ramStatusText').textContent = `${memory.available_mb || 0} MB liberi • Mem Stall: ${sysPressure.mem_stall_percent || 0}%`;

    // 6. Thermals & CPU
    document.getElementById('tempVal').textContent = `${thermals.battery_temp_c || 0} °C`;
    document.getElementById('throttleVal').textContent = thermals.thermal_status || 'Normal';
    document.getElementById('uptimeVal').textContent = dev.uptime_str || 'N/A';
    document.getElementById('thermalStatusNote').textContent = thermals.battery_temp_c >= 39
      ? 'Temperatură ridicată — folosește oprirea proceselor din fundal'
      : 'Temperatură în parametri optimi pentru procesor';

    // 7. ANR & Crashes
    const anrBadge = document.getElementById('anrCountBadge');
    anrBadge.textContent = `${anrs.total_anrs || 0} ANR / ${anrs.total_crashes || 0} Crash`;
    anrBadge.className = `badge ${anrs.status === 'critical' ? 'danger' : (anrs.status === 'warning' ? 'warning' : 'success')}`;

    const anrList = document.getElementById('anrList');
    anrList.innerHTML = '';
    const recentAnrs = anrs.recent_anrs || [];

    if (recentAnrs.length === 0) {
      anrList.innerHTML = '<div style="padding:16px; color:#4ade80; text-align:center;">Nu s-au găsit blocaje de tip "Not Responding" recente în jurnalele sistem!</div>';
    } else {
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
            <button class="btn btn-action-small" title="Oprește procesul, șterge doar cache-ul corupt și compilează nativ în mod speed (Nu șterge contul!)" onclick="executeOptimization('deep_repair_app', '${pkg}')">🔧 Repară (Păstrează Date)</button>
            <button class="btn btn-action-small btn-warn-small" title="Blochează aplicația din a rula în fundal" onclick="executeOptimization('restrict_app_background', '${pkg}')">🛑 Restricționează Fundal</button>
            <button class="btn btn-action-small btn-danger-small" title="Șterge toate datele aplicației (Necesită relogare)" onclick="executeOptimization('clear_package_cache', '${pkg}')">🗑️ Reset Complet</button>
          </div>
        `;
        anrList.appendChild(row);
      });
    }

    // 8. UI Jank / Frame Drop Apps List
    const jankAppsList = document.getElementById('jankAppsList');
    const jankBadge = document.getElementById('jankCountBadge');
    const jankyApps = uiFluency.janky_apps || [];
    jankBadge.textContent = `${jankyApps.length} Aplicații Analizate (${jankPct}% Jank Global)`;
    jankBadge.className = `badge ${jankPct >= 15 ? 'danger' : (jankPct >= 8 ? 'warning' : 'success')}`;

    jankAppsList.innerHTML = '';
    if (jankyApps.length === 0) {
      jankAppsList.innerHTML = '<div style="padding:14px; color:#94a3b8; text-align:center;">Nu există statistici de cadre pierdute momentan (sau tocmai au fost resetate). Folosește telefonul câteva minute și scanează din nou.</div>';
    } else {
      jankyApps.forEach(app => {
        const pkg = escapeHtml(app.package);
        const row = document.createElement('div');
        row.className = 'anr-row';
        row.innerHTML = `
          <div>
            <div class="anr-pkg" style="color:#93c5fd;">${pkg}</div>
            <div class="anr-meta">Cadre sacadate (Jank): <strong>${app.jank_percent}%</strong> (${app.janky_frames} din ${app.total_frames} cadre)</div>
            <div class="anr-meta" style="color:#94a3b8; font-size:0.75rem;">Timp randare 95th: ${app.p95_ms}ms • 99th: ${app.p99_ms}ms (Optim sub 8ms la 120Hz)</div>
          </div>
          <div class="row-actions">
            <button class="btn btn-action-small" onclick="executeOptimization('deep_repair_app', '${pkg}')">⚡ Compilează Speed & Curăță Cache</button>
          </div>
        `;
        jankAppsList.appendChild(row);
      });
    }

    // 9. Top Lists (RAM & CPU with direct stop buttons)
    const topRamList = document.getElementById('topRamList');
    topRamList.innerHTML = '';
    (memory.top_apps || []).forEach(app => {
      const pkg = escapeHtml(app.package);
      const li = document.createElement('li');
      li.innerHTML = `
        <span title="${pkg}">${pkg}</span>
        <div class="list-item-right">
          <span class="val-pill">${app.memory_mb} MB</span>
          <button class="btn-mini" title="Oprește forțat" onclick="executeOptimization('force_stop', '${pkg}')">Oprește</button>
        </div>
      `;
      topRamList.appendChild(li);
    });

    const topCpuList = document.getElementById('topCpuList');
    topCpuList.innerHTML = '';
    (thermals.top_cpu_apps || []).forEach(app => {
      const pkg = escapeHtml(app.package);
      const li = document.createElement('li');
      li.innerHTML = `
        <span title="${pkg}">${pkg}</span>
        <div class="list-item-right">
          <span class="val-pill">${app.cpu_percent}% CPU</span>
          <button class="btn-mini" title="Oprește și restricționează fundal" onclick="executeOptimization('restrict_app_background', '${pkg}')">Blochează</button>
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
    liveStepCounter.textContent = `Pasul ${job.step || 0} / ${job.total_steps || 1} (${pct}%)`;
    liveElapsedTimer.textContent = `⏱️ ${job.elapsed_sec || 0}s`;
    liveCurrentTaskBox.textContent = job.current_task || '';

    if (job.running) {
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = '🔄 ÎN CURS DE EXECUȚIE...';
      liveProgressBarFill.className = 'live-progress-fill running';
      liveFinishBanner.classList.add('hidden');
    } else if (job.completed) {
      if (job.success) {
        liveStatusBadge.className = 'badge success';
        liveStatusBadge.textContent = '✅ FINALIZAT CU SUCCES (100%)';
        liveProgressBarFill.className = 'live-progress-fill done';
      } else {
        liveStatusBadge.className = 'badge danger';
        liveStatusBadge.textContent = '⚠️ EROARE LA EXECUȚIE';
        liveProgressBarFill.className = 'live-progress-fill error';
      }
      liveFinishBanner.classList.remove('hidden');
      liveFinishText.textContent = job.result_message || 'Operațiunea s-a încheiat.';
    }

    // Render logs
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
        const res = await fetch('/api/job-status');
        if (!res.ok) return;
        const job = await res.json();
        renderJobStatus(job);
        if (!job.running && job.completed) {
          clearInterval(jobPollInterval);
          jobPollInterval = null;
          showToast('✅ ' + (job.result_message || 'Reparația s-a finalizat!'), 6000);
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
      const qs = activeDevice ? `?serial=${encodeURIComponent(activeDevice.serial)}` : '';
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
        showToast(`✅ S-au încărcat ${pkgs.length} pachete instalate pe telefon!`);
      }
    } catch (e) {
      console.error('Error loading packages:', e);
    }
  };

  window.runCustomAppAction = function(action) {
    const input = document.getElementById('customPkgInput');
    const pkg = (input?.value || '').trim();
    if (!pkg || !pkg.includes('.')) {
      alert('Te rugăm să selectezi sau să introduci un nume valid de pachet (ex: com.whatsapp, com.instagram.android)!');
      return;
    }
    window.executeOptimization(action, pkg);
  };

  // Global handler for action buttons
  window.executeOptimization = async function(action, pkg = null) {
    if (action === 'reboot') {
      if (!confirm('Ești sigur că vrei să repornești telefonul acum?')) return;
    } else if (action === 'clear_package_cache') {
      if (!confirm(`ATENȚIE: 'Reset Complet' va șterge toate datele și contul din aplicația ${pkg} (ca la reinstalare). Dacă vrei să păstrezi contul și doar să repari blocajele, anulează și apasă pe '🔧 Repară (Păstrează Date)'. Continui cu Reset Complet?`)) return;
    } else if (action === 'disable_accessibility') {
      if (!confirm('Dezactivezi serviciile de accesibilitate active pentru a elimina lag-ul la atingere și scroll?')) return;
    }

    // Show live console immediately
    if (liveConsoleCard) {
      liveConsoleCard.classList.remove('hidden');
      liveFinishBanner.classList.add('hidden');
      liveStatusBadge.className = 'badge warning';
      liveStatusBadge.textContent = '🔄 PORNIRE...';
      liveProgressBarFill.style.width = '5%';
      liveCurrentTaskBox.textContent = 'Se trimite comanda către telefon prin ADB...';
      liveConsoleCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    try {
      const res = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          package: pkg,
          serial: activeDevice ? activeDevice.serial : null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'Eroare');
      startJobPolling();
    } catch (err) {
      alert('Eroare la optimizare: ' + err.message);
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

  // Initial check & interval polling
  checkDeviceStatus();
  statusPollInterval = setInterval(checkDeviceStatus, 3000);
});
