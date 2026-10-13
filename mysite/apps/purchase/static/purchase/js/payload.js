export function buildBillPayload({
  cart,
  discountPercent,
  receivedAmount,
  deliveryCharges,
  remarks,
  Payment_method,
  card_detail,
  salesMan,
  acc_code,
  header_date,
  header_supl_inv_no,
  header_supl_inv_date,
  header_our_ref,
  header_our_ref_date,
  header_delivery_person,
  header_freight_amount,
  header_labour_amount,
  header_unload_amount,
  header_freight_acc_code,
  header_labour_acc_code,
  header_unload_acc_code,
  bill_no,
  billTypeRadioButton,
  // mapPaymentMode,
}) {

  billTypeRadioButton = document.querySelector('input[name="bill_type"]:checked');
  const is_return = billTypeRadioButton?.value === "return";

  const totalItemCount = cart.length;
  const totalAmountBeforeDiscount = cart.reduce((sum, item) => sum + (item.amount), 0);
  // const totalAmountBeforeDiscount = cart.reduce((sum, item) => sum + (item.baseTotal || (item.qty * item.rate)), 0);
  const calculatedDiscountAmount = (totalAmountBeforeDiscount * discountPercent) / 100;
  const calculatedNetTotal = totalAmountBeforeDiscount - calculatedDiscountAmount + deliveryCharges;
  const changeAmount = receivedAmount - calculatedNetTotal;
  let header_cash_paid = 0;
  let header_bank_paid = 0;


  if (!is_return) {
    const negativeItem = cart.find(item => Number(item.qty) < 0);
    

    if (negativeItem) {
      return {
        success: false,
        message: "Negative Qty not allowed in Purchase Bill!",
      };
    }

    
  }
  else{
    const positiveItem = cart.find(item => Number(item.qty) > 0);
    if (is_return && positiveItem){
      return {
        success: false,
        message: "Positive Qty not allowed in Purchase Return!",
      };
    }

  }
  

  // if (Payment_method === 'dual') {
  //   header_cash_paid = receivedAmount;
  //   header_bank_paid = calculatedNetTotal - receivedAmount;
  // } else if (Payment_method === 'cash') {
  //   header_cash_paid = receivedAmount;
  // } else if (Payment_method === 'card') {
  //   header_bank_paid = receivedAmount;
  // }
  if (Payment_method === '112000001') {
    header_cash_paid = receivedAmount;
  } else {
    header_bank_paid = receivedAmount;
  }
  const payload = {
    // Header Totals Mapping
    header_total_items: totalItemCount,
    header_item_total: totalAmountBeforeDiscount,
    header_discount_percent: discountPercent,
    header_discount_amount: calculatedDiscountAmount,
    header_msc_charges: deliveryCharges,
    header_net_total: calculatedNetTotal,
    header_remarks: remarks,

    date: header_date,

    header_acc_code: acc_code,
    salesman: salesMan,
    // Header Payment Mapping
    header_payment_mode: parseInt(Payment_method),
    header_bank_paid: header_bank_paid,
    header_cash_paid: header_cash_paid,
    header_card_last4: card_detail ? card_detail.slice(-4) : "",
    header_total_paid: receivedAmount,
    header_change_amount: changeAmount > 0 ? changeAmount : 0,


    header_supl_inv_no,
    header_supl_inv_date,
    header_our_ref,
    header_our_ref_date,
    header_delivery_person,
    header_freight_amount,
    header_labour_amount,
    header_unload_amount,
    header_freight_acc_code,
    header_labour_acc_code,
    header_unload_acc_code,


    // Row-level Items Mapping
    items: cart.map((item) => {
      // Calculate packaging quantity details (carton packing, dozen packing, etc.) dynamically based on qtyFactors
      const factor = item.qtyFactors && item.qtyFactors[item.packing_mode] ? item.qtyFactors[item.packing_mode] : 0;
      const uom = item.uoms && item.uoms[item.packing_mode] ? item.uoms[item.packing_mode] : null;
      let packQty = factor;

      const rowItem = {
        inv_id: item.id,
        prod_name: item.product_description,
        product_name_ur: item.prod_name_ur || "",
        qty: is_return && item.qty > 0 && false? -1 * item.qty : item.qty,
        rate: item.rate,
        packing_mode: item.packing_mode || 1,
        uom: uom,
        pack_qty: Number(packQty.toFixed(3)),
        row_discount_percent: item.discount_percent_per_item || 0,
        row_discount_amount: item.discount || 0,
        row_net_total: is_return && item.qty > 0 && false ? -1 * item.amount : item.amount || 0,
        row_old_total_base_qty: item.row_old_total_base_qty || 0,
      };

      // Dynamically attach all dynamic fields from the registry
      if (window.PURCHASE_CART_ROW_FIELDS) {
        for (const fieldName of Object.keys(window.PURCHASE_CART_ROW_FIELDS)) {
          rowItem[fieldName] = item[fieldName] !== undefined ? item[fieldName] : "";
        }
      }

      return rowItem;
    }),
  };

  if (bill_no) {
    payload.bill_no = bill_no;
  }
  if (is_return) {
    payload.is_return = true
  }

  return {
    success: true,
    payload: payload,
  };
}