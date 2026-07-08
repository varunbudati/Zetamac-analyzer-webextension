// content.js — Zetamac → Obsidian (Isolated World)
// Listens for game-end data from the interceptor (MAIN world) via postMessage,
// generates an Obsidian-flavored markdown note, and triggers the download.

(function () {
  'use strict';

  console.log('[Zetamac→Obsidian] Content script loaded.');

  // ── Listen for data from the MAIN-world interceptor via postMessage ──
  window.addEventListener('message', async function (e) {
    // Only process messages from our interceptor
    if (!e.data || e.data.source !== 'zetamac-obsidian-interceptor' || e.data.type !== 'GAME_END') {
      return;
    }

    const problemLog = e.data.problemLog;
    console.log('[Zetamac→Obsidian] Game ended. Problems:', problemLog.length);

    // Get settings from the background service worker
    let settings;
    try {
      settings = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }, (resp) => {
          if (chrome.runtime.lastError) {
            reject(chrome.runtime.lastError);
          } else {
            resolve(resp || { subfolder: 'Zetamac', autoDownload: true, vaultPath: '' });
          }
        });
      });
    } catch (err) {
      console.error('[Zetamac→Obsidian] Failed to get settings:', err);
      settings = { subfolder: 'Zetamac', autoDownload: true, vaultPath: '' };
    }

    // Parse the URL for game duration
    const urlParams = new URLSearchParams(window.location.search);
    const duration = parseInt(urlParams.get('s') || '120', 10);

    // Generate the markdown
    const markdown = generateMarkdown(problemLog, duration);
    const now = new Date();
    const filename = `Zetamac ${formatDate(now)} ${formatTime(now)}.md`;

    console.log('[Zetamac→Obsidian] Generated markdown for', filename);

    if (settings.autoDownload !== false) {
      chrome.runtime.sendMessage(
        {
          type: 'DOWNLOAD_MD',
          filename: filename,
          content: markdown,
          subfolder: settings.subfolder || '',
          vaultPath: settings.vaultPath || '',
        },
        (response) => {
          if (chrome.runtime.lastError) {
            console.error('[Zetamac→Obsidian] Download message failed:', chrome.runtime.lastError);
            showNotification('❌ Export failed — check extension settings', 'error');
          } else if (response && response.success) {
            const method = response.method === 'native' ? 'vault' : 'downloads';
            console.log('[Zetamac→Obsidian] File saved via', method);
            showNotification('✅ Session exported to Obsidian!', 'success');
          } else {
            console.error('[Zetamac→Obsidian] Download response error:', response);
            showNotification('⚠️ Export may have failed — check downloads', 'warning');
          }
        }
      );
    } else {
      // Copy to clipboard as fallback
      try {
        await navigator.clipboard.writeText(markdown);
        showNotification('📋 Copied to clipboard!', 'success');
      } catch {
        console.log('[Zetamac→Obsidian] Markdown:\n', markdown);
        showNotification('⚠️ Check console for markdown output', 'warning');
      }
    }
  });

  // ── Markdown Generation ──

  function generateMarkdown(problemLog, duration) {
    const now = new Date();

    // Separate solved problems from the final unsolved one
    const solved = problemLog.filter((p) => p.timeMs > 0);
    const unsolved = problemLog.filter((p) => p.timeMs <= 0);

    // Classify each solved problem by operation
    const classified = solved.map((p) => {
      const op = classifyOperation(p.problem);
      const userAnswer = p.entry ? p.entry[p.entry.length - 1] : String(p.answer);
      return {
        ...p,
        operation: op,
        userAnswer: userAnswer ? userAnswer.trim() : String(p.answer),
        correct: true, // Zetamac only logs correct answers
      };
    });

    // Stats by operation
    const ops = ['addition', 'subtraction', 'multiplication', 'division'];
    const opSymbols = { addition: '➕', subtraction: '➖', multiplication: '✖️', division: '➗' };
    const opStats = {};
    for (const op of ops) {
      const items = classified.filter((p) => p.operation === op);
      if (items.length === 0) continue;
      const times = items.map((p) => p.timeMs);
      opStats[op] = {
        count: items.length,
        avgMs: times.reduce((a, b) => a + b, 0) / times.length,
        slowest: Math.max(...times),
        fastest: Math.min(...times),
        items: items,
      };
    }

    const totalScore = solved.length;
    const allTimes = solved.map((p) => p.timeMs);
    const avgTimeMs = allTimes.length > 0 ? allTimes.reduce((a, b) => a + b, 0) / allTimes.length : 0;

    // Find the 5 slowest problems
    const slowest = [...classified].sort((a, b) => b.timeMs - a.timeMs).slice(0, 5);

    // Build YAML frontmatter
    const frontmatter = [
      '---',
      'tags: [zetamac, mental-math]',
      `date: ${formatDate(now)}`,
      `time: "${formatTime(now).replace('-', ':')}"`,
      `score: ${totalScore}`,
      `duration: ${duration}`,
      `avg_time_ms: ${Math.round(avgTimeMs)}`,
    ];
    for (const op of ops) {
      if (opStats[op]) {
        frontmatter.push(`${op}_count: ${opStats[op].count}`);
        frontmatter.push(`${op}_avg_ms: ${Math.round(opStats[op].avgMs)}`);
      }
    }
    frontmatter.push('---');

    // Build the markdown body
    const lines = [];
    lines.push(frontmatter.join('\n'));
    lines.push('');
    lines.push(`# Zetamac Session — ${formatPrettyDate(now)}`);
    lines.push('');

    // Summary table
    lines.push('## 📊 Summary');
    lines.push('');
    lines.push('| Operation | Solved | Avg Time | Fastest | Slowest |');
    lines.push('|-----------|--------|----------|---------|---------|');
    for (const op of ops) {
      if (opStats[op]) {
        const s = opStats[op];
        lines.push(
          `| ${opSymbols[op]} ${capitalize(op)} | ${s.count} | ${msToSec(s.avgMs)} | ${msToSec(s.fastest)} | ${msToSec(s.slowest)} |`
        );
      }
    }
    lines.push(
      `| **Total** | **${totalScore}** | **${msToSec(avgTimeMs)}** | — | — |`
    );
    lines.push('');

    // Slowest problems
    if (slowest.length > 0) {
      lines.push('## 🐌 Slowest Problems');
      lines.push('');
      lines.push('| # | Problem | Time | Answer | Operation |');
      lines.push('|---|---------|------|--------|-----------|');
      slowest.forEach((p, i) => {
        lines.push(
          `| ${i + 1} | ${prettifyProblem(p.problem)} | ${msToSec(p.timeMs)} | ${p.answer} | ${opSymbols[p.operation] || '?'} |`
        );
      });
      lines.push('');
    }

    // Unsolved problem (if timer ran out mid-problem)
    if (unsolved.length > 0) {
      lines.push('## ⏱️ Unsolved (Timer Expired)');
      lines.push('');
      unsolved.forEach((p) => {
        lines.push(`- **${prettifyProblem(p.problem)}** = ${p.answer}`);
      });
      lines.push('');
    }

    // Full log
    lines.push('## 📋 Full Log');
    lines.push('');
    lines.push('| # | Problem | Answer | Time |');
    lines.push('|---|---------|--------|------|');
    classified.forEach((p, i) => {
      lines.push(
        `| ${i + 1} | ${prettifyProblem(p.problem)} | ${p.answer} | ${msToSec(p.timeMs)} |`
      );
    });
    lines.push('');

    // Areas to improve
    lines.push('## 💡 Areas to Improve');
    lines.push('');

    // Find weakest operation (slowest average)
    const opEntries = Object.entries(opStats);
    if (opEntries.length > 1) {
      const slowestOp = opEntries.sort((a, b) => b[1].avgMs - a[1].avgMs)[0];
      lines.push(
        `- **${capitalize(slowestOp[0])}** is your slowest operation (avg ${msToSec(slowestOp[1].avgMs)}) — focus your practice here`
      );
    }

    // Find specific slow patterns
    if (slowest.length > 0) {
      const slowDivisions = slowest.filter((p) => p.operation === 'division');
      const slowMultiplications = slowest.filter((p) => p.operation === 'multiplication');

      if (slowDivisions.length > 0) {
        const divisors = slowDivisions
          .map((p) => {
            const parts = p.problem.split('/');
            return parts.length > 1 ? parts[1].trim() : '';
          })
          .filter(Boolean);
        if (divisors.length > 0) {
          lines.push(`- Practice dividing by: ${[...new Set(divisors)].join(', ')}`);
        }
      }

      if (slowMultiplications.length > 0) {
        const factors = slowMultiplications.map((p) => {
          const parts = p.problem.split('*');
          return parts.map((x) => x.trim());
        });
        const uniqueFactors = [...new Set(factors.flat())];
        if (uniqueFactors.length > 0) {
          lines.push(`- Practice multiplying with: ${uniqueFactors.join(', ')}`);
        }
      }

      // General advice based on slowest problems
      const avgSlowest = slowest.reduce((a, p) => a + p.timeMs, 0) / slowest.length;
      if (avgSlowest > 5000) {
        lines.push('- Your slowest problems take over 5 seconds — try breaking large numbers into parts');
      } else if (avgSlowest > 3000) {
        lines.push('- Some problems take 3+ seconds — practice estimation and rounding strategies');
      }
    }

    // Score-based advice
    if (totalScore < 30) {
      lines.push('- Focus on speed with easier ranges before increasing difficulty');
    } else if (totalScore < 50) {
      lines.push('- Good progress! Try to identify and eliminate your 3 slowest problem types');
    } else {
      lines.push('- Excellent score! Consider increasing the number ranges for a greater challenge');
    }

    lines.push('');
    return lines.join('\n');
  }

  // ── Utility Functions ──

  function classifyOperation(plainProblem) {
    if (plainProblem.includes('+')) return 'addition';
    if (plainProblem.includes('-')) return 'subtraction';
    if (plainProblem.includes('*')) return 'multiplication';
    if (plainProblem.includes('/')) return 'division';
    return 'unknown';
  }

  function prettifyProblem(plain) {
    return plain
      .replace(/\*/g, '×')
      .replace(/\//g, '÷')
      .replace(/-/g, '−');
  }

  function msToSec(ms) {
    return (ms / 1000).toFixed(1) + 's';
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function formatTime(d) {
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    return `${h}-${m}`;
  }

  function formatPrettyDate(d) {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
  }

  // ── Toast Notification ──

  function showNotification(message, type = 'success') {
    const existing = document.getElementById('zetamac-obsidian-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'zetamac-obsidian-toast';
    toast.textContent = message;
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      padding: '14px 24px',
      borderRadius: '12px',
      color: '#fff',
      fontSize: '15px',
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      fontWeight: '600',
      zIndex: '999999',
      boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
      backdropFilter: 'blur(12px)',
      transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      transform: 'translateY(20px)',
      opacity: '0',
      background:
        type === 'success'
          ? 'linear-gradient(135deg, #7c3aed, #a855f7)'
          : 'linear-gradient(135deg, #f59e0b, #ef4444)',
    });

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
      toast.style.transform = 'translateY(0)';
      toast.style.opacity = '1';
    });

    // Animate out after 4s
    setTimeout(() => {
      toast.style.transform = 'translateY(20px)';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  }
})();
