/*
 * ═══════ GLOBAL ACCOUNT MODAL — Vanilla JS ═══════
 *
 * Usage:
 *   1. {% include 'myaccounts/global_account_form_modal.html' %}
 *   2. Call:  openAccountModal('10000001')   → load & show
 *             openAccountModal()             → blank / new
 *
 * API:
 *   GET  /myaccounts/api/get/<acc_code>/    → returns JSON
 *   POST /myaccounts/api/save/<acc_code>/   → saves via FormData (request.POST)
 */
import {Helpers} from "/static/myaccounts/js/services/account_utils.js";



    const API_GET = (code) => `/myaccounts/api/get/${parseInt(code)}/`;
    const API_SAVE = (code) => `/myaccounts/api/save/${parseInt(code)}/`;

    const FIELDS = [
        'ACC_CODE', 'ACC_NAME', 'SALESMAN',
        'MOBILE_NO', 'PHONE_OFF', 'EMAIL_ADDRESS',
        'ADDRESS', 'CITY', 'COUNTRY',
        'OPENING_BALANCE', 'BALANCE_TYPE', 'CREDIT_LIMIT',
        'NTN_NO', 'STN_NO', 'REMARKS', 'PASSWORD', 'LOCKED',
        'CLASS_FIELD', 'LEVEL', 'TYPE'
    ];

    const el = (id) => document.getElementById(id);

    /* ── Message helpers ── */
    function showMsg(text, type) {
        const box = el('accModalMsg');
        box.textContent = text;
        box.className = 'acc-modal__msg acc-modal__msg--' + type;
        box.style.display = 'block';
    }

    function hideMsg() {
        el('accModalMsg').style.display = 'none';
    }

    /* ── Form helpers ── */
    function clearForm() {
        FIELDS.forEach(f => {
            const input = el('accm_' + f);
            if (!input) return;
            if (input.type === 'checkbox') input.checked = false;
            else input.value = '';
        });
        const hidden = el('update_or_create');
        if (hidden) hidden.value = '';
        hideMsg();
    }

    function fillForm(data) {
        FIELDS.forEach(f => {
            const input = el('accm_' + f);
            if (!input || data[f] === undefined) return;
            if (input.type === 'checkbox') input.checked = !!data[f];
            else input.value = data[f] !== null ? data[f] : '';
        });
        const hidden = el('update_or_create');
        if (hidden && data.update_or_create) {
            hidden.value = data.update_or_create;
        }
    }

    function collectFormData() {
        const fd = new FormData();
        FIELDS.forEach(f => {
            const input = el('accm_' + f);
            if (!input) return;
            if (input.type === 'checkbox') fd.append(f, input.checked ? 'true' : 'false');
            else fd.append(f, input.value);
        });
        return fd;
    }

    /* ── Modal show / hide ── */
    function openModal() { el('accModal').style.display = 'flex'; }
    function closeModal() { el('accModal').style.display = 'none'; clearForm(); }

    /* ── CSRF Token from cookie ── */
    window.getCSRFToken = function getCSRFToken() {
        const match = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return match ? match.split('=')[1] : '';
    }

    /* ══════════════════════════════════════
       MAIN — call from anywhere
       openAccountModal('231000001')
       openAccountModal()
    ══════════════════════════════════════ */
    export const openAccountModal = async function (accCode, level = null, showOnlyName = false) {
        clearForm();
        openModal();
        
        const classAndType = Helpers.getClassFieldAndAccountTypeByStartingCode(accCode,level);
        if(classAndType){
            el('accm_TYPE').value = classAndType.accType;
            el('accm_CLASS_FIELD').value = classAndType.classField;
        }
        console.log('accCode' , accCode)
        console.log('level' , level)
        console.log('classAndType' , classAndType)
        

        if (!accCode) {
            el('accModalTitle').textContent = 'New Account';
            el('accm_ACC_CODE').removeAttribute('readonly');
            return;
        }
        if (showOnlyName) {
            el('showOnlyName').style.display = 'none';
        }else{
            el('showOnlyName').style.display = 'block';
        }
        el('accModalTitle').textContent = 'Account — ' + accCode;
        el('accm_ACC_CODE').setAttribute('readonly', true);
        el('accm_ACC_CODE').value = accCode;

        if (level) {
            el('accm_LEVEL').value = level;
        }
        showMsg('Loading...', 'loading');
        const hidden = el('accm_UPDATE_OR_CREATE');
        try {
            const res = await fetch(API_GET(accCode));
            const data = await res.json();

            if (res.ok) {
                if (data.update_or_create == 'update') {
                    if (hidden) hidden.value = data.update_or_create || 'update';
                    showMsg(`${data.message}`, 'success');
                    // showMsg(`greate`, 'success'); 

                    fillForm(data.data);
                }
                else {
                    if (hidden) hidden.value = data.update_or_create || 'create';
                    showMsg(`${data.message}`, 'success');
                }
                // hideMsg();
            } else {
                if (hidden) hidden.value = data.update_or_create || 'create';
                showMsg(`${data.message}`, 'success');
            }
        } catch (err) {
            console.log('error', err);
            showMsg('Network error', 'error');
        }
    };

    /* ── Save / Update ── */
    async function saveAccount() {
        const accCode = el('accm_ACC_CODE')?.value || '';

        if (!accCode) {
            showMsg('Account code is required', 'error');
            return;
        }

        showMsg('Saving...', 'loading');

        try {
            const res = await fetch(API_SAVE(accCode), {
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCSRFToken() },
                body: collectFormData()
            });
            console.log('collectFormData()',collectFormData())
            const result = await res.json();

            if (res.ok) {
                showMsg(result.success || result.message || 'Saved successfully!', 'success');
            } else {
                showMsg(result.error || 'Save failed', 'error');
            }
        } catch (err) {
            showMsg('Network error', 'error');
        }
    }
    el('accModalSave').addEventListener('click', saveAccount);
    el('accModalClose').addEventListener('click', closeModal);
    el('accModalCancel').addEventListener('click', closeModal);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            e.preventDefault()
            closeModal();
            // console.log('Escape key pressed');
        }
    });



