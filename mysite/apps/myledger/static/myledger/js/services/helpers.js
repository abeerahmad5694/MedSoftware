const myLedgerHelpers = {
  banks_api_url: '/myledger/api/get_banks/',
  save_dynamic_voucher_api_url: '/myledger/api/save_dynamic_voucher/',
  delete_dynamic_voucher_api_url: '/myledger/api/delete_dynamic_voucher/',
  get_voucher_for_edit_api_url: '/myledger/api/get_voucher_for_edit/',
  get_general_ledger_api_url: '/myledger/api/general_ledger/',
  
  getBanks: async () => {
    const response = await fetch(myLedgerHelpers.banks_api_url);
    const data = await response.json();
    if (data.success) {
      return data.data;
    } else {
      console.error(data.error);
      return null;
    }
  },
  getCookie: function (name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  },
  saveUpdateDynamicVoucher: async (payload) => {
    const response = await fetch(myLedgerHelpers.save_dynamic_voucher_api_url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': myLedgerHelpers.getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (data.success) {
      return data;
    } else {
      return data;
    }
  },

  deleteDynamicVoucher: async (payload) => {
    const response = await fetch(myLedgerHelpers.delete_dynamic_voucher_api_url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': myLedgerHelpers.getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (data.success) {
      return data;
    } else {
      return data;
    }
  },

  getDynamicVoucherForEdit: async (vno, v_type) => {
    const response = await fetch(myLedgerHelpers.get_voucher_for_edit_api_url + vno + '/' + v_type + '/');
    const data = await response.json();
    if (data.success) {
      return data;
    } else {
      return data;
    }
  },


  getGeneralLedger: async (accCode, fromDate, toDate) => {
    const response = await fetch(myLedgerHelpers.get_general_ledger_api_url + accCode + '/' + fromDate + '/' + toDate + '/');
    const data = await response.json();
    if (data.success) {
      return data;
    } else {
      return data;
    }
  },

}



export default myLedgerHelpers;