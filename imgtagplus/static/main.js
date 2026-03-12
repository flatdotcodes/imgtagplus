/** Frontend controller for the single-page tagging UI and its long-running job state. */

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    
    // UI Elements
    const modelSelect = document.getElementById('model-select');
    const modelWarning = document.getElementById('model-warning');
    const inputPath = document.getElementById('input-path');
    const thresholdInput = document.getElementById('threshold');
    const thresholdVal = document.getElementById('threshold-val');
    const maxTagsInput = document.getElementById('max-tags');
    const maxTagsVal = document.getElementById('max-tags-val');
    const recursiveCheck = document.getElementById('recursive');
    const overwriteCheck = document.getElementById('overwrite');
    const startBtn = document.getElementById('start-btn');
    const errorMsg = document.getElementById('error-msg');
    
    // Progress Elements
    const progressTitle = document.getElementById('progress-title');
    const progressFile = document.getElementById('progress-file');
    const progressPct = document.getElementById('progress-pct');
    const progressCounts = document.getElementById('progress-counts');
    const progressBar = document.getElementById('progress-bar');
    const runtimeClock = document.getElementById('runtime-clock');
    const logContainer = document.getElementById('log-container');
    const clearLogsBtn = document.getElementById('clear-logs');
    const copyLogsBtn = document.getElementById('copy-logs');
    const downloadLogBtn = document.getElementById('download-log');

    // Stats Elements
    const statsContainer = document.getElementById('stats-container');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    // Hardware Elements
    const hardwarePanel = document.getElementById('hardware-panel');
    const ramSpec = document.getElementById('ram-spec');
    const accelSpec = document.getElementById('accel-spec');
    const perfRating = document.getElementById('perf-rating');
    
    // Dialogs (native <dialog> elements)
    const helpDialog = document.getElementById('help-dialog');
    const perfDialog = document.getElementById('perf-dialog');
    const accelDialog = document.getElementById('accel-dialog');
    const filePickerDialog = document.getElementById('file-picker-dialog');

    // Dialog openers
    const helpBtn = document.getElementById('help-btn');
    const accelBox = document.getElementById('accel-box');
    const perfBox = document.getElementById('perf-box');
    const browseBtn = document.getElementById('browse-btn');

    // File Picker Elements
    const cancelFilePickerBtn = document.getElementById('cancel-file-picker');
    const selectDirBtn = document.getElementById('select-dir-btn');
    const dirList = document.getElementById('dir-list');
    const currentDirPathSpan = document.getElementById('current-dir-path');
    const sandboxWarning = document.getElementById('sandbox-warning');

    // Output Dir Elements
    const outputToggle = document.getElementById('show-output-dir');
    const outputDirFields = document.getElementById('output-dir-fields');
    const outputDirInput = document.getElementById('output-dir');
    const outputBrowseBtn = document.getElementById('output-browse-btn');

    // Manual Accelerator Elements
    const manualAccelToggle = document.getElementById('manual-accelerator');
    const manualAccelStatus = document.getElementById('manual-accel-status');
    const accelOptionsDiv = document.getElementById('accelerator-options');
    const accelRadios = document.getElementsByName('accel-choice');
    const accelCuda = document.getElementById('accel-cuda');
    const accelMps = document.getElementById('accel-mps');
    const accelCpu = document.getElementById('accel-cpu');
    const labelCuda = document.getElementById('label-accel-cuda');
    const labelMps = document.getElementById('label-accel-mps');
    const tipCuda = document.getElementById('tip-cuda');
    const tipMps = document.getElementById('tip-mps');
    const dialogStates = new WeakMap();
    const themeController = window.imgtagplusTheme;

    // Click handlers for tips (ensures visibility on mobile/click)
    [tipCuda, tipMps].forEach(tip => {
        tip.addEventListener('click', (e) => {
            const msg = tip.getAttribute('data-tooltip');
            if (msg) alert(msg);
            e.preventDefault();
            e.stopPropagation();
        });
    });

    // State shared across event handlers. `isProcessing` mirrors backend status; `eventSource`
    // is the single SSE pipe used to stream progress/log events for the active job.
    let models = [];
    let isProcessing = false;
    let eventSource = null;
    let runtimeTimer = null;
    let currentBrowsePath = "";
    let browseTarget = 'input'; // 'input' or 'output' — which field the file picker populates
    let detectedAccelerator = 'cpu';
    let lastManualAccelerator = 'cpu';

    // ----- Slider Progress -----

    function updateSliderProgress(input) {
        const min = parseFloat(input.min) || 0;
        const max = parseFloat(input.max) || 100;
        const val = parseFloat(input.value);
        const progress = ((val - min) / (max - min)) * 100;
        input.style.setProperty('--slider-value', `${progress}%`);
    }

    function getSelectedAccelerator() {
        return Array.from(accelRadios).find((radio) => radio.checked)?.value || null;
    }

    function formatRuntime(totalSeconds) {
        const safeSeconds = Math.max(0, Math.floor(totalSeconds));
        const hours = String(Math.floor(safeSeconds / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((safeSeconds % 3600) / 60)).padStart(2, '0');
        const seconds = String(safeSeconds % 60).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    function renderRuntime(totalSeconds = 0) {
        runtimeClock.textContent = formatRuntime(totalSeconds);
    }

    function stopRuntimeTimer() {
        if (runtimeTimer) {
            window.clearInterval(runtimeTimer);
            runtimeTimer = null;
        }
    }

    function startRuntimeTimer(startedAtValue = new Date().toISOString()) {
        const startedAt = new Date(startedAtValue);

        stopRuntimeTimer();
        if (Number.isNaN(startedAt.getTime())) {
            renderRuntime(0);
            return;
        }

        const tick = () => renderRuntime((Date.now() - startedAt.getTime()) / 1000);
        tick();
        runtimeTimer = window.setInterval(tick, 1000);
    }

    function syncRuntimeFromStatus(statusData) {
        if (statusData.is_processing && statusData.started_at) {
            startRuntimeTimer(statusData.started_at);
            return;
        }

        if (statusData.is_processing) {
            if (!runtimeTimer) {
                startRuntimeTimer();
            }
            return;
        }

        stopRuntimeTimer();
        if (typeof statusData.runtime_seconds === 'number') {
            renderRuntime(statusData.runtime_seconds);
        }
    }

    function setSelectedAccelerator(value) {
        const availableRadio = Array.from(accelRadios).find((radio) => radio.value === value && !radio.disabled)
            || Array.from(accelRadios).find((radio) => radio.value === detectedAccelerator && !radio.disabled)
            || Array.from(accelRadios).find((radio) => !radio.disabled);

        if (availableRadio) {
            availableRadio.checked = true;
            lastManualAccelerator = availableRadio.value;
        }
    }

    function getEffectiveAccelerator() {
        return manualAccelToggle.checked
            ? (getSelectedAccelerator() || lastManualAccelerator || detectedAccelerator)
            : detectedAccelerator;
    }

    function syncAcceleratorUI() {
        if (manualAccelToggle.checked && (!getSelectedAccelerator() || document.querySelector('input[name="accel-choice"]:checked')?.disabled)) {
            setSelectedAccelerator(lastManualAccelerator);
        }

        const effectiveAccelerator = getEffectiveAccelerator();
        manualAccelStatus.textContent = manualAccelToggle.checked
            ? `enabled (${effectiveAccelerator.toUpperCase()})`
            : 'disabled';
        accelOptionsDiv.classList.toggle('hidden', !manualAccelToggle.checked);
        accelSpec.textContent = manualAccelToggle.checked
            ? `${effectiveAccelerator.toUpperCase()} (manual)`
            : detectedAccelerator.toUpperCase();
    }

    // ----- Initialization -----

    async function init() {
        try {
            const sysRes = await fetch('/api/system');
            const data = await sysRes.json();
            
            models = data.models;
            
            // Populate Hardware
            ramSpec.textContent = `${data.hardware.total_ram_gb} GB (${data.hardware.available_ram_gb} GB free)`;
            accelSpec.textContent = data.hardware.accelerator.toUpperCase();
            perfRating.textContent = data.performance_rating;
            
            // Animate Hardware Panel In
            setTimeout(() => {
                 hardwarePanel.classList.remove('opacity-0');
            }, 500);
            
            // Populate Models
            modelSelect.innerHTML = '';
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.key;
                opt.textContent = `${m.name} ${m.supported ? '' : '(Not Recommended)'}`;
                if (!m.supported && !m.recommended) {
                    opt.disabled = true;
                }
                modelSelect.appendChild(opt);
            });
            
            updateModelWarning();

            // Set up Manual Accelerator options based on system capabilities
            const sysAccel = data.hardware.accelerator;
            detectedAccelerator = sysAccel;
            lastManualAccelerator = sysAccel;
            if (sysAccel === 'cuda') {
                accelCuda.disabled = false;
                labelCuda.classList.remove('text-muted-foreground');
                labelCuda.classList.add('text-foreground');
                accelCpu.disabled = false;
                accelCuda.checked = true;
                
                // Show tip for unavailable option
                tipMps.classList.remove('hidden');
            } else if (sysAccel === 'mps') {
                accelMps.disabled = false;
                labelMps.classList.remove('text-muted-foreground');
                labelMps.classList.add('text-foreground');
                accelCpu.disabled = false;
                accelMps.checked = true;
                
                // Show tip for unavailable option
                tipCuda.classList.remove('hidden');
            } else {
                // Only CPU
                accelCpu.disabled = false;
                accelCpu.checked = true;
                
                // Show tips for both
                tipCuda.classList.remove('hidden');
                tipMps.classList.remove('hidden');
            }

            syncAcceleratorUI();

            // If the page is refreshed mid-run, restore the locked UI and reconnect to the stream.
            const statusRes = await fetch('/api/status');
            const statusData = await statusRes.json();
            syncRuntimeFromStatus(statusData);
            if (statusData.is_processing) {
                setProcessingState(true);
            }

        } catch (e) {
            console.error(e);
            errorMsg.textContent = "Failed to connect to backend api.";
            errorMsg.classList.remove("hidden");
        }
    }

    init();
    updateSliderProgress(thresholdInput);
    updateSliderProgress(maxTagsInput);

    // ----- Event Listeners -----

    thresholdInput.addEventListener('input', (e) => {
        thresholdVal.textContent = e.target.value;
        updateSliderProgress(e.target);
    });

    maxTagsInput.addEventListener('input', (e) => {
        maxTagsVal.textContent = e.target.value;
        updateSliderProgress(e.target);
    });

    modelSelect.addEventListener('change', updateModelWarning);
    startBtn.addEventListener('click', startJob);

    clearLogsBtn.addEventListener('click', () => {
        logContainer.innerHTML = '';
        addLog({level: "INFO", message: "Logs cleared."});
    });

    copyLogsBtn.addEventListener('click', async () => {
        const logText = Array.from(logContainer.children)
            .map((entry) => entry.innerText.trim())
            .filter(Boolean)
            .join('\n');

        if (!logText) {
            addLog({level: "INFO", message: "No log output available to copy."});
            return;
        }

        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(logText);
            } else {
                const copyBuffer = document.createElement('textarea');
                copyBuffer.value = logText;
                copyBuffer.setAttribute('readonly', '');
                copyBuffer.style.position = 'absolute';
                copyBuffer.style.left = '-9999px';
                document.body.appendChild(copyBuffer);
                copyBuffer.select();
                document.execCommand('copy');
                document.body.removeChild(copyBuffer);
            }

            addLog({level: "INFO", message: "Copied terminal output to clipboard."});
        } catch (error) {
            console.error('Failed to copy terminal output:', error);
            addLog({level: "ERROR", message: "Failed to copy terminal output to clipboard."});
        }
    });

    downloadLogBtn.addEventListener('click', () => {
        window.open('/api/logs/download', '_blank');
    });

    // Output location toggle
    outputToggle.addEventListener('change', () => {
        if (outputToggle.checked) {
            outputDirFields.classList.remove('hidden');
        } else {
            outputDirFields.classList.add('hidden');
            outputDirInput.value = '';
        }
    });

    // Manual Accelerator toggle
    manualAccelToggle.addEventListener('change', () => {
        if (manualAccelToggle.checked) {
            setSelectedAccelerator(lastManualAccelerator);
        }
        syncAcceleratorUI();
    });

    Array.from(accelRadios).forEach((radio) => {
        radio.addEventListener('change', () => {
            if (radio.checked) {
                lastManualAccelerator = radio.value;
                syncAcceleratorUI();
            }
        });
    });
    
    function syncHelpDialogState() {
        const darkToggle = document.getElementById('dark-mode-toggle');
        const darkLabel = document.getElementById('dark-mode-label');
        if (darkToggle) {
            const isDark = document.documentElement.classList.contains('dark');
            darkToggle.checked = isDark;
            if (darkLabel) darkLabel.innerHTML = isDark
                ? 'Dark mode <span class="font-medium">enabled</span>'
                : 'Light mode <span class="font-medium">enabled</span>';
        }
    }

    function openDialog(dialog, options = {}) {
        if (!dialog || dialog.open) {
            return;
        }

        const state = {
            opener: options.opener ?? document.activeElement,
            onClose: options.onClose ?? null
        };

        dialogStates.set(dialog, state);
        if (typeof options.beforeOpen === 'function') {
            options.beforeOpen();
        }
        dialog.showModal();
    }

    function cleanupDialog(dialog) {
        const state = dialogStates.get(dialog) ?? {};
        const activeElement = document.activeElement;

        if (activeElement && dialog.contains(activeElement) && typeof activeElement.blur === 'function') {
            activeElement.blur();
        }

        if (typeof state.onClose === 'function') {
            state.onClose(state);
        }

        dialogStates.delete(dialog);
    }

    function requestDialogClose(dialog) {
        if (dialog?.open) {
            dialog.close();
        }
    }

    function wireDialog(dialog, options = {}) {
        if (!dialog) {
            return;
        }

        dialog.addEventListener('click', (event) => {
            if (event.target === dialog) {
                requestDialogClose(dialog);
            }
        });

        dialog.addEventListener('cancel', (event) => {
            event.preventDefault();
            requestDialogClose(dialog);
        });

        dialog.addEventListener('close', () => cleanupDialog(dialog));

        dialog.querySelectorAll('[data-dialog-close]').forEach((button) => {
            button.addEventListener('click', () => requestDialogClose(dialog));
        });
    }

    wireDialog(helpDialog);
    wireDialog(perfDialog);
    wireDialog(accelDialog);
    wireDialog(filePickerDialog);

    // Dialog openers — native showModal()
    helpBtn.addEventListener('click', () => openDialog(helpDialog, {
        opener: helpBtn,
        beforeOpen: syncHelpDialogState,
        onClose: ({ opener }) => opener?.blur()
    }));
    accelBox.addEventListener('click', () => openDialog(accelDialog, {
        opener: accelBox,
        beforeOpen: syncAcceleratorUI
    }));
    perfBox.addEventListener('click', () => openDialog(perfDialog, { opener: perfBox }));

    // Dark mode toggle in Help dialog
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const darkModeLabel = document.getElementById('dark-mode-label');
    darkModeToggle.addEventListener('change', () => {
        const mode = darkModeToggle.checked ? 'dark' : 'light';
        if (themeController?.applyTheme) {
            themeController.applyTheme(mode);
        } else {
            document.dispatchEvent(new CustomEvent('basecoat:theme', { detail: { mode } }));
        }
        if (darkModeLabel) darkModeLabel.innerHTML = darkModeToggle.checked
            ? 'Dark mode <span class="font-medium">enabled</span>'
            : 'Light mode <span class="font-medium">enabled</span>';
    });
    
    browseBtn.addEventListener('click', () => {
        browseTarget = 'input';
        openFilePicker(inputPath.value.trim());
    });

    outputBrowseBtn.addEventListener('click', () => {
        browseTarget = 'output';
        openFilePicker(outputDirInput.value.trim());
    });

    cancelFilePickerBtn.addEventListener('click', () => requestDialogClose(filePickerDialog));
    
    selectDirBtn.addEventListener('click', () => {
        if (currentBrowsePath) {
            if (browseTarget === 'output') {
                outputDirInput.value = currentBrowsePath;
            } else {
                inputPath.value = currentBrowsePath;
            }
        }
        requestDialogClose(filePickerDialog);
    });

    // ----- Functions -----

    function updateModelWarning() {
        const selected = models.find(m => m.key === modelSelect.value);
        if (selected && !selected.supported) {
            modelWarning.textContent = selected.warning;
            modelWarning.classList.remove('hidden');
        } else {
            modelWarning.classList.add('hidden');
        }
        
        // Hide threshold for VLM as they don't use it the same way CLIP does
        const thresholdGroup = thresholdInput.closest('.grid');
        if (selected && selected.type === "vlm") {
             if (thresholdGroup) thresholdGroup.style.opacity = '0.5';
             thresholdInput.disabled = true;
        } else {
             if (thresholdGroup) thresholdGroup.style.opacity = '1';
             thresholdInput.disabled = false;
        }
    }

    function openFilePicker(initialPath = "") {
        const opener = browseTarget === 'output' ? outputBrowseBtn : browseBtn;
        openDialog(filePickerDialog, { opener });
        loadDirectory(initialPath);
    }

    async function loadDirectory(path) {
        // The browser cannot enumerate local folders directly, so the dialog proxies every step
        // through `/api/browse` and redraws from the server's constrained view of the filesystem.
        dirList.innerHTML = '<div class="p-4 text-center text-sm text-muted-foreground">Loading...</div>';
        try {
            const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
            const data = await res.json();
            
            if (!res.ok) {
                dirList.innerHTML = `<div class="p-4 text-center text-sm text-destructive">${escapeHtml(data.detail || 'Unknown error')}</div>`;
                return;
            }
            
            currentBrowsePath = data.current_path;
            currentDirPathSpan.textContent = data.current_path;
            
            if (data.sandbox) {
                sandboxWarning.classList.remove('hidden');
            } else {
                sandboxWarning.classList.add('hidden');
            }
            
            dirList.innerHTML = '';
            if (data.items.length === 0) {
                dirList.innerHTML = '<div class="p-4 text-center text-sm text-muted-foreground">Folder is empty</div>';
                return;
            }
            
            data.items.forEach(item => {
                const btn = document.createElement('button');
                btn.className = "w-full text-left px-3 py-2 text-sm rounded-md hover:bg-muted/50 focus:bg-muted/50 focus:outline-none transition-colors flex items-center gap-3 group";
                
                let icon = '';
                if (item.name === "..") {
                    icon = `<svg class="text-muted-foreground group-hover:text-foreground transition-colors shrink-0" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>`;
                } else {
                    icon = `<svg class="text-blue-500/80 shrink-0" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>`;
                }
                
                btn.innerHTML = `${icon}<span class="truncate">${escapeHtml(item.name)}</span>`;
                btn.onclick = () => loadDirectory(item.path);
                dirList.appendChild(btn);
            });
            
        } catch (e) {
             dirList.innerHTML = `<div class="p-4 text-center text-sm text-destructive">Failed to load directory</div>`;
        }
    }

    async function startJob() {
        if (isProcessing) return;
        
        const path = inputPath.value.trim();
        if (!path) {
            errorMsg.textContent = "Please provide a directory path.";
            errorMsg.classList.remove("hidden");
            return;
        }
        
        errorMsg.classList.add("hidden");
        // Flip the UI into the running state before the POST resolves so double-submits are blocked
        // and the SSE connection is ready to receive the first progress event immediately.
        setProcessingState(true);

        try {
            const payload = {
                input: path,
                model_id: modelSelect.value,
                threshold: parseFloat(thresholdInput.value),
                max_tags: parseInt(maxTagsInput.value),
                recursive: recursiveCheck.checked,
                overwrite: overwriteCheck.checked
            };

            if (manualAccelToggle.checked) {
                payload.accelerator = getEffectiveAccelerator();
            }

            // Only send optional fields the backend should actually honor for this run.
            if (outputToggle.checked && outputDirInput.value.trim()) {
                payload.output_dir = outputDirInput.value.trim();
            }

            const res = await fetch('/api/tag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Unknown error');
            }
            
            logContainer.innerHTML = '';
            const acceleratorLabel = manualAccelToggle.checked
                ? `${payload.accelerator?.toUpperCase()} (manual)`
                : `${detectedAccelerator.toUpperCase()} (auto)`;
            addLog({level: "INFO", message: `Starting job via ${modelSelect.value} on ${acceleratorLabel}...`});
            if (data.started_at) {
                startRuntimeTimer(data.started_at);
            }

        } catch (e) {
            errorMsg.textContent = e.message;
            errorMsg.classList.remove("hidden");
            setProcessingState(false);
        }
    }

    function setProcessingState(processing) {
        // Centralize the "job is running" transition so button state, inputs, status text and SSE
        // lifecycle never drift apart when init(), startJob() or stream events toggle it.
        isProcessing = processing;
        inputPath.disabled = processing;
        modelSelect.disabled = processing;
        thresholdInput.disabled = processing;
        maxTagsInput.disabled = processing;
        recursiveCheck.disabled = processing;
        overwriteCheck.disabled = processing;

        if (processing) {
            startBtn.disabled = true;
            startBtn.innerHTML = `<svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Processing...`;
            
            statusText.textContent = "Running";
            statusDot.className = "w-2 h-2 rounded-full bg-green-500 animate-pulse";
            if (!runtimeTimer) {
                startRuntimeTimer();
            }
            
            connectSSE();
        } else {
            startBtn.disabled = false;
            startBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Tagging`;
            
            statusText.textContent = "Idle";
            statusDot.className = "w-2 h-2 rounded-full bg-zinc-500";
            stopRuntimeTimer();
            
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        }
    }

    function connectSSE() {
        if (eventSource) return;
        
        eventSource = new EventSource('/api/stream');
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'progress') {
                if (data.done) {
                    // Completion is signaled on the stream, not the original POST response.
                    setProcessingState(false);
                    progressTitle.textContent = "Finished";
                    progressFile.textContent = "Task complete.";
                    progressBar.style.width = "100%";
                    progressBar.classList.remove('bg-primary');
                    progressBar.classList.add('bg-green-500');
                    if (typeof data.runtime_seconds === 'number') {
                        renderRuntime(data.runtime_seconds);
                    }
                    return;
                }
                
                progressBar.classList.add('bg-primary');
                progressBar.classList.remove('bg-green-500');
                
                progressTitle.textContent = "Tagging";
                
                let fileD = data.filename.split('/').pop();
                progressFile.textContent = fileD ? `.../${fileD}` : data.filename;
                
                if (data.total > 0) {
                    const pct = Math.round((data.current / data.total) * 100);
                    progressBar.style.width = `${pct}%`;
                    progressPct.textContent = `${pct}%`;
                    progressCounts.textContent = `${data.current} / ${data.total} images`;
                }
                if (typeof data.runtime_seconds === 'number') {
                    renderRuntime(data.runtime_seconds);
                }
            } 
            else if (data.type === 'log') {
                addLog(data);
            }
            else if (data.type === 'idle') {
                // `/api/status` can reconnect us to a stale stream after a refresh; an explicit idle
                // event is the backend's way to tell the frontend that nothing is actively running.
                if(isProcessing) {
                    setProcessingState(false);
                }
            }
        };
        
        eventSource.onerror = () => {
             console.error("SSE connection lost. Reconnecting...");
        };
    }

    function addLog(data) {
        const div = document.createElement('div');
        div.className = "flex gap-3 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 px-2 rounded -mx-2 transition-colors";

        let colorClass = "text-zinc-700 dark:text-zinc-400";
        if (data.level === 'WARNING') colorClass = "text-yellow-600 dark:text-yellow-500";
        if (data.level === 'ERROR' || data.level === 'CRITICAL') colorClass = "text-red-600 dark:text-red-500";
        if (data.level === 'DEBUG') colorClass = "text-zinc-500 dark:text-zinc-600";

        const time = new Date().toLocaleTimeString([], {hour12: false});

        div.innerHTML = `
            <span class="text-zinc-500 dark:text-zinc-600 shrink-0 w-16">${time}</span>
            <span class="${colorClass} shrink-0 w-12 text-xs font-semibold mt-[2px]">${escapeHtml(data.level || "LOG")}</span>
            <span class="text-zinc-800 dark:text-zinc-300 break-all whitespace-pre-wrap">${escapeHtml(data.message)}</span>
        `;        logContainer.appendChild(div);
        
        logContainer.scrollTop = logContainer.scrollHeight;
    }

});
