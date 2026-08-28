(function () {
  'use strict';

  var generateBtn = document.getElementById('generate-btn');
  var emailBlockSection = document.getElementById('email-block-section');
  var emailBlock = document.getElementById('email-block');
  var copyBtn = document.getElementById('copy-btn');
  var copyConfirm = document.getElementById('copy-confirm');
  var noSelectionHint = document.getElementById('no-selection-hint');

  // Handle URL hash tab activation if tabs exist
  function handleHashTab() {
    var hash = window.location.hash;
    if (hash) {
      var tabTrigger = document.querySelector('button[data-bs-target="' + hash + '"], a[href="' + hash + '"]');
      if (tabTrigger && typeof bootstrap !== 'undefined' && bootstrap.Tab) {
        var tab = bootstrap.Tab.getOrCreateInstance(tabTrigger);
        tab.show();
      }
    }
  }

  // Listen for tab changes to update URL hash and toggle card highlights
  var tabButtons = document.querySelectorAll('button[data-bs-toggle="pill"], button[data-bs-toggle="tab"]');
  tabButtons.forEach(function (btn) {
    btn.addEventListener('shown.bs.tab', function (e) {
      var target = e.target.getAttribute('data-bs-target');
      if (target && history.replaceState) {
        history.replaceState(null, null, target);
      }
      // Toggle highlight on the summary cards to match the active tab
      var cardClassic = document.getElementById('card-classic');
      var cardCustom = document.getElementById('card-custom');
      if (cardClassic && cardCustom) {
        if (target === '#classic') {
          cardClassic.classList.add('highlight');
          cardCustom.classList.remove('highlight');
        } else if (target === '#custom') {
          cardCustom.classList.add('highlight');
          cardClassic.classList.remove('highlight');
        }
      }
    });
  });

  // Data tab switch buttons (e.g., custom trigger buttons)
  var switchButtons = document.querySelectorAll('[data-tab-switch]');
  switchButtons.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var targetId = btn.getAttribute('data-tab-switch');
      var targetTabBtn = document.querySelector('button[data-bs-target="' + targetId + '"]');
      if (targetTabBtn && typeof bootstrap !== 'undefined' && bootstrap.Tab) {
        var tab = bootstrap.Tab.getOrCreateInstance(targetTabBtn);
        tab.show();
      }
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', handleHashTab);
  } else {
    handleHashTab();
  }

  if (!generateBtn) return;

  function buildBlock() {
    var journalChecks = Array.from(document.querySelectorAll('input[name="journal"]:checked'));
    var osfChecks = Array.from(document.querySelectorAll('input[name="osf_category"]:checked'));

    if (journalChecks.length === 0 && osfChecks.length === 0) {
      return null;
    }

    var lines = [];
    lines.push('#PICNIC v1 BEGIN');
    lines.push('action: subscribe');

    journalChecks.forEach(function (cb) {
      var label = document.querySelector('label[for="' + cb.id + '"]');
      var name = label ? label.textContent.trim() : cb.value;
      lines.push('journal: ' + cb.value + '   (' + name + ')');
    });

    osfChecks.forEach(function (cb) {
      var label = document.querySelector('label[for="' + cb.id + '"]');
      var name = label ? label.textContent.trim() : cb.value;
      lines.push('preprint: ' + cb.value + '   (' + name + ')');
    });

    lines.push('#PICNIC END');
    return lines.join('\n');
  }

  function updateBlock() {
    var block = buildBlock();
    if (block === null) {
      emailBlockSection.classList.add('d-none');
      noSelectionHint.classList.remove('d-none');
    } else {
      noSelectionHint.classList.add('d-none');
      emailBlock.textContent = block;
      emailBlockSection.classList.remove('d-none');
    }
    copyConfirm.classList.add('d-none');
  }

  generateBtn.addEventListener('click', updateBlock);

  // Live-update when checkboxes change (only if block already visible)
  document.addEventListener('change', function (e) {
    if (e.target && (e.target.name === 'journal' || e.target.name === 'osf_category')) {
      if (!emailBlockSection.classList.contains('d-none') || !noSelectionHint.classList.contains('d-none')) {
        updateBlock();
      }
    }
  });

  copyBtn.addEventListener('click', function () {
    var text = emailBlock.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        copyConfirm.classList.remove('d-none');
        setTimeout(function () { copyConfirm.classList.add('d-none'); }, 2500);
      }).catch(fallbackCopy);
    } else {
      fallbackCopy();
    }
  });

  function fallbackCopy() {
    var ta = document.createElement('textarea');
    ta.value = emailBlock.textContent;
    ta.style.position = 'fixed';
    ta.style.top = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      copyConfirm.classList.remove('d-none');
      setTimeout(function () { copyConfirm.classList.add('d-none'); }, 2500);
    } catch (err) {
      // silent failure
    }
    document.body.removeChild(ta);
  }

})();

