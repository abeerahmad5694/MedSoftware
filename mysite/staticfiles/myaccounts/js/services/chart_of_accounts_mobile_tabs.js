/**
 * COA Mobile Tab Switcher
 * Only activates on mobile (≤ 860px). Desktop layout is untouched.
 */
(function () {
    const DETAIL_LEVEL = 4;
    const BREAKPOINT = 860;

    const leftPane   = document.querySelector('.coa-pane--left');
    const rightPane  = document.querySelector('.coa-pane--right');
    const tabGroups  = document.getElementById('tab-groups');
    const tabDetails = document.getElementById('tab-details');

    if (!leftPane || !rightPane || !tabGroups || !tabDetails) {
        console.warn('[COA Tabs] Required elements not found. Tab switcher skipped.');
        return;
    }

    function isMobile() {
        return window.innerWidth <= BREAKPOINT;
    }

    function switchTab(which) {
        if (!isMobile()) return;   // desktop: do nothing

        const showLeft = which === 'groups';
        leftPane.classList.toggle('panel-hidden', !showLeft);
        rightPane.classList.toggle('panel-hidden', showLeft);

        tabGroups.classList.toggle('active', showLeft);
        tabDetails.classList.toggle('active', !showLeft);
    }

    // Expose globally so onclick="switchTab(...)" in HTML works
    window.switchTab = switchTab;

    // On resize: if going back to desktop, remove any hidden classes
    window.addEventListener('resize', function () {
        if (!isMobile()) {
            leftPane.classList.remove('panel-hidden');
            rightPane.classList.remove('panel-hidden');
        }
    });

    // Auto-switch to details panel when a Level-3 group is clicked
    document.getElementById('tree-root')?.addEventListener('click', function (e) {
        const row = e.target.closest('[data-level="' + 
            `${DETAIL_LEVEL-1}` + '"] .node-header, .node-row[data-nid]');
        if (row && isMobile()) {
            switchTab('details');
        }
    });

}());