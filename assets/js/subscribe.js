(function () {
  'use strict';

  var generateBtn = document.getElementById('generate-btn');
  var emailBlockSection = document.getElementById('email-block-section');
  var emailBlock = document.getElementById('email-block');
  var copyBtn = document.getElementById('copy-btn');
  var copyConfirm = document.getElementById('copy-confirm');
  var noSelectionHint = document.getElementById('no-selection-hint');

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
