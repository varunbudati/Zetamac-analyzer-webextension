// background.js — Service worker for Zetamac → Obsidian
// Handles file save requests via native messaging (direct vault path) or Chrome downloads API (fallback).

const NATIVE_HOST = 'com.zetamac.obsidian';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'ANALYZE_PROGRESSION') {
    const { vaultPath } = message;
    if (vaultPath && vaultPath.trim()) {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST,
        {
          action: 'analyze',
          vaultPath: vaultPath.trim(),
        },
        (response) => {
          if (chrome.runtime.lastError) {
            console.error(
              '[Zetamac→Obsidian] Native messaging failed:',
              chrome.runtime.lastError.message
            );
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
          } else if (response && response.success) {
            sendResponse({ success: true, path: response.path });
          } else {
            sendResponse({ success: false, error: response?.error || 'Unknown host error' });
          }
        }
      );
    } else {
      sendResponse({ success: false, error: 'Vault path not configured.' });
    }
    return true; // async
  }

  if (message.type === 'DOWNLOAD_MD') {
    const { filename, content, subfolder, vaultPath } = message;

    // If a vault path is configured, use native messaging for direct write
    if (vaultPath && vaultPath.trim()) {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST,
        {
          vaultPath: vaultPath.trim(),
          filename: filename,
          content: content,
        },
        (response) => {
          if (chrome.runtime.lastError) {
            console.warn(
              '[Zetamac→Obsidian] Native messaging failed, falling back to downloads:',
              chrome.runtime.lastError.message
            );
            // Fall back to downloads API
            downloadViaChrome(filename, content, subfolder, sendResponse);
          } else if (response && response.success) {
            console.log('[Zetamac→Obsidian] File written to vault:', response.path);
            sendResponse({ success: true, path: response.path, method: 'native' });
          } else {
            console.error('[Zetamac→Obsidian] Native host error:', response?.error);
            // Fall back to downloads API
            downloadViaChrome(filename, content, subfolder, sendResponse);
          }
        }
      );
    } else {
      // No vault path — use Chrome downloads API
      downloadViaChrome(filename, content, subfolder, sendResponse);
    }

    return true; // async response
  }

  if (message.type === 'GET_SETTINGS') {
    chrome.storage.sync.get(
      { subfolder: 'Zetamac', autoDownload: true, vaultPath: '' },
      (items) => {
        sendResponse(items);
      }
    );
    return true;
  }
});

function downloadViaChrome(filename, content, subfolder, sendResponse) {
  const relativePath = subfolder
    ? `${subfolder.replace(/[\\/]+$/, '')}/${filename}`
    : filename;

  const blob = new Blob([content], { type: 'text/markdown' });
  const reader = new FileReader();
  reader.onloadend = () => {
    const dataUrl = reader.result;
    chrome.downloads.download(
      {
        url: dataUrl,
        filename: relativePath,
        saveAs: false,
        conflictAction: 'uniquify',
      },
      (downloadId) => {
        if (chrome.runtime.lastError) {
          console.error('[Zetamac→Obsidian] Download failed:', chrome.runtime.lastError.message);
          sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
          console.log('[Zetamac→Obsidian] Download started, ID:', downloadId);
          sendResponse({ success: true, downloadId, method: 'download' });
        }
      }
    );
  };
  reader.readAsDataURL(blob);
}
