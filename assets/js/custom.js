// ====================
// Utility Functions
// ====================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ====================
// Filter Banner Logic
// ====================

function updateFilterBanner() {
    const $banner = $('#filter-banner');
    if (!$banner.length) return;

    let filterMessage = '';
    let hasActiveFilters = false;

    // Check journal filters
    const discipline = getDisciplineFromPath(window.location.pathname);
    if (discipline) {
        const storageKey = `journal_settings_${discipline}`;
        const settings = StorageUtil.get(storageKey);
        if (settings) {
            const hiddenCount = settings.filter(s => !s.visible).length;
            const totalCount = settings.length;
            if (hiddenCount > 0) {
                hasActiveFilters = true;
                filterMessage = `Filters active: ${hiddenCount} of ${totalCount} journals hidden`;
            }
        }
    }

    // Check preprints filters
    const preprintsKey = 'preprints_visible_groups';
    const visibleGroups = StorageUtil.get(preprintsKey);
    if (visibleGroups !== null) {
        const $subjectContainer = $('#subject-settings-list');
        if ($subjectContainer.length) {
            const totalGroups = $subjectContainer.find('.subject-visibility').length;
            const hiddenCount = totalGroups - visibleGroups.length;
            if (hiddenCount > 0) {
                hasActiveFilters = true;
                filterMessage = `Filters active: ${hiddenCount} of ${totalGroups} subject groups hidden`;
            }
        }
    }

    if (hasActiveFilters) {
        // Reset dismissed state when filters change
        StorageUtil.remove('filter_banner_dismissed');
        $('#filter-banner-message').text(filterMessage);
        $banner.show();
    } else {
        $banner.hide();
    }
}

function setupFilterBannerDismiss() {
    $('#filter-banner-dismiss').on('click', function() {
        StorageUtil.setRaw('filter_banner_dismissed', 'true');
        $('#filter-banner').hide();
    });
}

// ====================
// Initialization
// ====================

$(function () {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').each((_, el) => new bootstrap.Tooltip(el));

    initJournalSettings();
    initPreprintsSettings();
    setupFilterBannerDismiss();
    updateFilterBanner();
});

// ====================
// Journal Settings Logic
// ====================

function initJournalSettings() {
    const discipline = getDisciplineFromPath(window.location.pathname);
    if (!discipline) {
        console.log('No discipline detected from path');
        return;
    }

    const storageKey = `journal_settings_${discipline}`;
    const $container = $('#journal-settings-list');

    // Check if the settings container exists on this page
    if (!$container.length) {
        console.log('Settings container not found on this page');
        return;
    }

    console.log('Initializing journal settings for:', discipline);
    const settings = StorageUtil.get(storageKey);
    console.log('Loaded settings:', settings);

    // Extract journals from pre-rendered DOM (only IDs, not names)
    const domJournals = $container.find('.draggable-item').map(function () {
        return { id: $(this).data('id'), visible: true };
    }).get();

    let currentSettings = settings || domJournals;

    if (settings) {
        const domJournalIds = new Set(domJournals.map(j => j.id));
        // Remove journals no longer in DOM, add new journals from DOM
        currentSettings = settings.filter(s => domJournalIds.has(s.id));
        domJournals.forEach(dj => {
            if (!currentSettings.some(s => s.id === dj.id)) currentSettings.push(dj);
        });
    }

    StorageUtil.set(storageKey, currentSettings);

    applySettingsToDOM(currentSettings, $container);
    initSortable($container);
    setupEventListeners(storageKey);
    initGlobalSettings();
}

function initGlobalSettings() {
    const expandAuto = StorageUtil.getRaw('expandAbstracts') === 'true';
    $('#global-expand-abstracts').prop('checked', expandAuto);
    if (expandAuto) applyAbstractExpansion(true);
}

function applyAbstractExpansion(expand) {
    $('.collapse-article').toggleClass('show', expand);
    $('[data-bs-target=".collapse-article"]').attr('aria-expanded', expand);
}

function applySettingsToDOM(settings, $container) {
    settings.forEach(s => {
        const $item = $container.find(`.draggable-item[data-id="${s.id}"]`);
        if ($item.length) {
            $item.find('.journal-visibility').prop('checked', s.visible);
            $item.appendTo($container);
        }
    });

    applyMainViewSettings(settings);
}

function initSortable($container) {
    const containerEl = $container[0];
    if (containerEl) {
        Sortable.create(containerEl, {
            handle: '.drag-handle',
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: () => saveCurrentSettings($container)
        });
    }
}

function saveCurrentSettings($container) {
    const discipline = getDisciplineFromPath(window.location.pathname);
    const storageKey = `journal_settings_${discipline}`;
    const currentSettings = StorageUtil.get(storageKey, []);

    const newOrder = $container.find('.draggable-item').map(function () {
        const id = $(this).data('id');
        return currentSettings.find(s => s.id === id);
    }).get().filter(Boolean);

    StorageUtil.set(storageKey, newOrder);
    applyMainViewSettings(newOrder);
}

function getDisciplineFromPath(path) {
    const disciplines = ['political_science', 'economics', 'sociology', 'multidisciplinary', 'migration_studies', 'communication_studies', 'public_administration', 'environmental_studies', 'international_relations'];
    const d = disciplines.find(d => path.includes(d));
    if (d) return d;
    const cleanPath = path.replace(/\/$/, "");
    return (cleanPath === "" || cleanPath.endsWith("index.html") || cleanPath.endsWith("picnic-v2")) ? 'political_science' : null;
}

function setupEventListeners(storageKey) {
    const $settingsOffcanvas = document.getElementById('settingsOffcanvas');

    if ($settingsOffcanvas) {
        $settingsOffcanvas.addEventListener('hidden.bs.offcanvas', function () {
            applyMainViewSettings(StorageUtil.get(storageKey));
        });
    }

    $('#reset-to-default').on('click', () => resetToDefaults(storageKey));

    $('#global-expand-abstracts').on('change', function () {
        const isChecked = $(this).is(':checked');
        StorageUtil.setRaw('expandAbstracts', isChecked);
        applyAbstractExpansion(isChecked);
    });

    $('#journal-settings-list').on('change', '.journal-visibility', function () {
        const $item = $(this).closest('.draggable-item');
        const settings = StorageUtil.get(storageKey);
        const s = settings.find(s => s.id === $item.data('id'));
        if (s) {
            s.visible = $(this).is(':checked');
            StorageUtil.set(storageKey, settings);
            applyMainViewSettings(settings);
            updateFilterBanner();
        }
    });
}

function resetToDefaults(storageKey) {
    let settings = StorageUtil.get(storageKey, []);

    // Set all to visible
    settings.forEach(s => s.visible = true);

    // Sort alphabetically by journal name from DOM
    settings.sort((a, b) => {
        const nameA = $(`.draggable-item[data-id="${a.id}"]`).find('label').text().trim();
        const nameB = $(`.draggable-item[data-id="${b.id}"]`).find('label').text().trim();
        return nameA.localeCompare(nameB);
    });

    // Save
    StorageUtil.set(storageKey, settings);

    // Update DOM (Checkboxes, List Order, Main View)
    settings.forEach(s => {
        $(`.draggable-item[data-id="${s.id}"]`)
            .find('.journal-visibility').prop('checked', true).end()
            .appendTo('#journal-settings-list');
    });

    applyMainViewSettings(settings);
    updateFilterBanner();
}

function applyMainViewSettings(settings) {
    const $parent = $('#articles-view');
    settings.forEach(s => {
        const $target = $(`#${s.id}`);
        if ($target.length) {
            $target.toggle(s.visible).appendTo($parent);
        }
    });
}

// ====================
// Navbar Scroll
// ====================

const handleNavbarScroll = debounce(() => {
    $('.navbar-custom').toggleClass('scrolled', $(window).scrollTop() > 20);
}, 10);

$(window).on('scroll', handleNavbarScroll);

// ====================
// Theme Switcher
// ====================

(() => {
    'use strict'

    const getStoredTheme = () => StorageUtil.getRaw('theme')
    const setStoredTheme = theme => StorageUtil.setRaw('theme', theme)

    const getPreferredTheme = () => {
        const storedTheme = getStoredTheme()
        if (storedTheme) {
            return storedTheme
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }

    const setTheme = theme => {
        document.documentElement.setAttribute('data-theme', theme)
        document.documentElement.setAttribute('data-bs-theme', theme)
    }

    setTheme(getPreferredTheme())

    const showActiveTheme = (theme) => {
        const themeSwitcher = document.querySelector('#bd-theme')
        const themeIconActive = document.querySelector('.theme-icon-active use')

        if (!themeSwitcher || !themeIconActive) {
            return
        }

        const themeIconMap = {
            'light': '#sun',
            'dark': '#moon-stars'
        }

        themeIconActive.setAttribute('href', themeIconMap[theme] || '#sun')

        // Update aria-label
        const nextTheme = theme === 'dark' ? 'light' : 'dark'
        themeSwitcher.setAttribute('aria-label', `Switch to ${nextTheme} mode`)
    }

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const storedTheme = getStoredTheme()
        if (!storedTheme) {
            const preferredTheme = getPreferredTheme()
            setTheme(preferredTheme)
            showActiveTheme(preferredTheme)
        }
    })

    window.addEventListener('DOMContentLoaded', () => {
        const currentTheme = getPreferredTheme()
        showActiveTheme(currentTheme)

        const toggleBtn = document.querySelector('#bd-theme')
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const currentTheme = document.documentElement.getAttribute('data-theme') || 'light'
                const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'

                setStoredTheme(nextTheme)
                setTheme(nextTheme)
                showActiveTheme(nextTheme)
            })
        }
    })
})()

// ====================
// BibTeX Citation Logic
// ====================

async function fetchBibTeX(doi) {
    const response = await fetch(doi, {
        headers: { 'Accept': 'application/x-bibtex' }
    });

    if (!response.ok) {
        throw new Error('Network response was not ok');
    }

    return response.text();
}

function resetButton($btn, text, delay = 2000) {
    setTimeout(() => {
        $btn.text(text).prop('disabled', false);
    }, delay);
}

$(document).on('click', '.btn-bibtex', async function () {
    const $btn = $(this);
    const doi = $btn.data('doi');

    // Prevent multiple clicks
    if ($btn.prop('disabled')) return;

    $btn.text('Loading...').prop('disabled', true);

    try {
        const bibtex = await fetchBibTeX(doi);
        await navigator.clipboard.writeText(bibtex);
        $btn.text('Copied!');
        resetButton($btn, 'BibTeX');
    } catch (err) {
        console.error('BibTeX fetch failed:', err);
        $btn.text('Failed');
        resetButton($btn, 'BibTeX');
    }
});

// ====================
// Preprints Settings Logic
// ====================

function initPreprintsSettings() {
    const $subjectContainer = $('#subject-settings-list');

    // Check if this is the preprints page
    if (!$subjectContainer.length) {
        return;
    }

    const storageKey = 'preprints_visible_groups';
    let visibleGroupIds = StorageUtil.get(storageKey, null);

    // If no settings saved, use Political Science as default
    if (visibleGroupIds === null) {
        const politicalScienceId = $('#subject-settings-list .subject-visibility').first().data('group-id');
        visibleGroupIds = [politicalScienceId];
        StorageUtil.set(storageKey, visibleGroupIds);
    }

    // Apply saved settings to checkboxes
    visibleGroupIds.forEach(groupId => {
        $(`#group-${CSS.escape(groupId)}`).prop('checked', true);
    });

    // Apply filtering to preprint cards
    applyGroupFiltering(visibleGroupIds);

    // Setup event listeners
    setupPreprintsEventListeners(storageKey);
    initGlobalSettings();
}

function setupPreprintsEventListeners(storageKey) {
    const $settingsOffcanvas = document.getElementById('settingsOffcanvas');

    if ($settingsOffcanvas) {
        $settingsOffcanvas.addEventListener('hidden.bs.offcanvas', function () {
            const visibleGroupIds = StorageUtil.get(storageKey, []);
            applyGroupFiltering(visibleGroupIds);
        });
    }

    $('#reset-to-default').on('click', () => resetPreprintsToDefaults(storageKey));

    $('#global-expand-abstracts').on('change', function () {
        const isChecked = $(this).is(':checked');
        StorageUtil.setRaw('expandAbstracts', isChecked);
        applyAbstractExpansion(isChecked);
    });

    $('#subject-settings-list').on('change', '.subject-visibility', function () {
        const groupId = $(this).data('group-id');
        let visibleGroupIds = StorageUtil.get(storageKey, []);

        if ($(this).is(':checked')) {
            // Add to visible list
            if (!visibleGroupIds.includes(groupId)) {
                visibleGroupIds.push(groupId);
            }
        } else {
            // Remove from visible list
            visibleGroupIds = visibleGroupIds.filter(id => id !== groupId);
        }

        StorageUtil.set(storageKey, visibleGroupIds);
        applyGroupFiltering(visibleGroupIds);
        updateFilterBanner();
    });
}

function resetPreprintsToDefaults(storageKey) {
    const politicalScienceId = $('#subject-settings-list .subject-visibility').first().data('group-id');
    const defaultVisible = [politicalScienceId];

    StorageUtil.set(storageKey, defaultVisible);

    $('.subject-visibility').prop('checked', false);
    $(`#group-${CSS.escape(politicalScienceId)}`).prop('checked', true);

    applyGroupFiltering(defaultVisible);
    updateFilterBanner();
}

function applyGroupFiltering(visibleGroupIds) {
    if (visibleGroupIds.length === 0) {
        $('.preprint-card').hide();
        return;
    }

    const subjectToGroupMap = buildSubjectToGroupMap();
    const visibleGroupSet = new Set(visibleGroupIds);
    const showNotClassified = visibleGroupSet.has('xxx');

    $('.preprint-card').each(function () {
        const $card = $(this);
        const subjectsAttr = $card.attr('data-subjects');

        if (!subjectsAttr || subjectsAttr.trim() === '') {
            $card.toggle(showNotClassified);
            return;
        }

        const cardSubjects = subjectsAttr.split(',').map(s => s.trim()).filter(s => s);
        const hasVisibleGroup = cardSubjects.some(subjectId => {
            const groupId = subjectToGroupMap[subjectId];
            return groupId && visibleGroupSet.has(groupId);
        });

        $card.toggle(hasVisibleGroup);
    });
}

function buildSubjectToGroupMap() {
    const map = {};
    const dataElement = document.getElementById('osf-subjects-data');

    if (dataElement) {
        try {
            const data = JSON.parse(dataElement.textContent);
            data.subgroups?.forEach(subgroup => {
                subgroup.osf?.forEach(subject => {
                    map[subject.id] = subgroup.id;
                });
            });
        } catch (e) {
            console.error('Failed to parse osf_subjects data:', e);
        }
    }

    return map;
}