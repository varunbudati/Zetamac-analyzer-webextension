// popup.js — Zetamac → Obsidian settings popup

document.addEventListener('DOMContentLoaded', () => {
  const vaultPathInput = document.getElementById('vaultPath');
  const subfolderInput = document.getElementById('subfolder');
  const autoDownloadToggle = document.getElementById('autoDownload');
  const saveBtn = document.getElementById('save');
  const methodIndicator = document.getElementById('methodIndicator');

  // Load saved settings
  chrome.storage.sync.get(
    { vaultPath: '', subfolder: 'Zetamac', autoDownload: true },
    (items) => {
      vaultPathInput.value = items.vaultPath || '';
      subfolderInput.value = items.subfolder || '';
      autoDownloadToggle.checked = items.autoDownload !== false;
      updateMethodIndicator(items.vaultPath);
    }
  );

  // Save settings
  saveBtn.addEventListener('click', () => {
    const settings = {
      vaultPath: vaultPathInput.value.trim(),
      subfolder: subfolderInput.value.trim(),
      autoDownload: autoDownloadToggle.checked,
    };

    chrome.storage.sync.set(settings, () => {
      if (chrome.runtime.lastError) {
        saveBtn.textContent = '❌ Error';
        console.error(chrome.runtime.lastError);
      } else {
        saveBtn.textContent = '✓ Saved!';
        saveBtn.classList.add('saved');
        updateMethodIndicator(settings.vaultPath);

        setTimeout(() => {
          saveBtn.textContent = 'Save Settings';
          saveBtn.classList.remove('saved');
        }, 1500);
      }
    });
  });

  // Allow Enter key to save
  vaultPathInput.addEventListener('keydown', handleEnter);
  subfolderInput.addEventListener('keydown', handleEnter);

  function handleEnter(e) {
    if (e.key === 'Enter') saveBtn.click();
  }

  // Test Connection logic
  const testBtn = document.getElementById('test');
  testBtn.addEventListener('click', () => {
    testBtn.textContent = 'Testing...';
    testBtn.className = 'btn btn-secondary testing';

    const vaultPath = vaultPathInput.value.trim();
    const subfolder = subfolderInput.value.trim();

    chrome.runtime.sendMessage(
      {
        type: 'DOWNLOAD_MD',
        filename: 'Zetamac Test Connection.md',
        content: '# Zetamac Connection Test\n\nYour Zetamac → Obsidian extension is working correctly!\n\n- Path: ' + (vaultPath || 'Downloads/' + subfolder) + '\n- Time: ' + new Date().toLocaleString() + '\n',
        subfolder: subfolder,
        vaultPath: vaultPath,
      },
      (response) => {
        if (chrome.runtime.lastError) {
          testBtn.textContent = '❌ Fail: Extension Error';
          testBtn.className = 'btn btn-secondary error';
          console.error('[Zetamac→Obsidian] Test error:', chrome.runtime.lastError.message);
        } else if (response && response.success) {
          if (response.method === 'native') {
            testBtn.textContent = '✅ Direct Write Success!';
            testBtn.className = 'btn btn-secondary success';
          } else {
            testBtn.textContent = '⚠️ Fallback: Downloads Folder';
            testBtn.className = 'btn btn-secondary error';
            console.warn('[Zetamac→Obsidian] Test completed but fell back to Downloads folder.');
          }
        } else {
          testBtn.textContent = '❌ Fail: Native Host Error';
          testBtn.className = 'btn btn-secondary error';
        }

        setTimeout(() => {
          testBtn.textContent = 'Test Connection';
          testBtn.className = 'btn btn-secondary';
        }, 3000);
      }
    );
  });
 
  // View Progression Dashboard logic
  const analyzeBtn = document.getElementById('analyze');
  analyzeBtn.addEventListener('click', () => {
    analyzeBtn.textContent = 'Analyzing...';
    analyzeBtn.className = 'btn btn-secondary testing';
 
    const vaultPath = vaultPathInput.value.trim();
 
    if (!vaultPath) {
      analyzeBtn.textContent = '❌ Fail: Path is empty';
      analyzeBtn.className = 'btn btn-secondary error';
      setTimeout(() => {
        analyzeBtn.textContent = '📊 View Progression Dashboard';
        analyzeBtn.className = 'btn btn-secondary';
      }, 3000);
      return;
    }
 
    chrome.runtime.sendMessage(
      {
        type: 'ANALYZE_PROGRESSION',
        vaultPath: vaultPath,
      },
      (response) => {
        if (chrome.runtime.lastError) {
          analyzeBtn.textContent = '❌ Fail: Extension Error';
          analyzeBtn.className = 'btn btn-secondary error';
          console.error('[Zetamac→Obsidian] Analysis error:', chrome.runtime.lastError.message);
        } else if (response && response.success) {
          analyzeBtn.textContent = '✅ Dashboard Opened!';
          analyzeBtn.className = 'btn btn-secondary success';
        } else {
          const errorMsg = response?.error || 'Host Error';
          // Truncate error message if it is too long for the button
          const displayError = errorMsg.length > 20 ? errorMsg.substring(0, 17) + '...' : errorMsg;
          analyzeBtn.textContent = `❌ Fail: ${displayError}`;
          analyzeBtn.className = 'btn btn-secondary error';
          console.error('[Zetamac→Obsidian] Analysis failed:', errorMsg);
        }
 
        setTimeout(() => {
          analyzeBtn.textContent = '📊 View Progression Dashboard';
          analyzeBtn.className = 'btn btn-secondary';
        }, 3000);
      }
    );
  });

  function updateMethodIndicator(vaultPath) {
    if (vaultPath && vaultPath.trim()) {
      methodIndicator.innerHTML =
        'Mode: <span class="method-native">📂 Direct write</span> → native messaging';
    } else {
      methodIndicator.innerHTML =
        'Mode: <span class="method-download">⬇️ Download</span> → Chrome downloads folder';
    }
  }
});
