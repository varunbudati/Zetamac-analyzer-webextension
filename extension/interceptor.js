// interceptor.js — Runs in the PAGE's main world (world: "MAIN")
// Monkey-patches jQuery.ajax to capture the problemLog when Zetamac posts to /log.

(function () {
  'use strict';

  console.log('[Zetamac→Obsidian] Interceptor script loaded, waiting for jQuery...');

  const waitForJQuery = setInterval(function () {
    if (typeof jQuery !== 'undefined' && jQuery.ajax) {
      clearInterval(waitForJQuery);
      installHook();
    }
  }, 100);

  // Safety timeout — stop waiting after 30 seconds
  setTimeout(function () {
    clearInterval(waitForJQuery);
  }, 30000);

  function installHook() {
    const originalAjax = jQuery.ajax;

    jQuery.ajax = function () {
      // jQuery.ajax can be called as ajax(url, settings) or ajax(settings)
      let settings;
      if (typeof arguments[0] === 'string') {
        settings = arguments[1] || {};
        settings.url = arguments[0];
      } else {
        settings = arguments[0] || {};
      }

      // Detect the /log POST that Zetamac makes at game end
      // jQuery 3.x uses lowercase "post" for type
      const isLogPost =
        settings.url === '/log' &&
        (settings.type || settings.method || '').toUpperCase() === 'POST';

      if (isLogPost) {
        console.log('[Zetamac→Obsidian] Intercepted /log POST!');
        try {
          const data = settings.data || {};
          const problemLogStr = data.problemLog;
          if (problemLogStr) {
            const problemLog = JSON.parse(problemLogStr);
            console.log('[Zetamac→Obsidian] Problem log captured:', problemLog.length, 'entries');

            // Use postMessage to send data to the content script (isolated world)
            window.postMessage({
              source: 'zetamac-obsidian-interceptor',
              type: 'GAME_END',
              problemLog: problemLog,
            }, '*');
          } else {
            console.warn('[Zetamac→Obsidian] /log POST had no problemLog in data:', data);
          }
        } catch (e) {
          console.error('[Zetamac→Obsidian] Failed to parse problem log:', e);
        }
      }

      return originalAjax.apply(this, arguments);
    };

    console.log('[Zetamac→Obsidian] jQuery.ajax hook installed successfully. (jQuery ' + jQuery.fn.jquery + ')');
  }
})();
