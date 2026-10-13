export function buildBillPayload({
  cart,
  discountPercent,
  receivedAmount,
  deliveryCharges,
  gstPercent,
  mscCharges,
  remarks,
  Payment_method,
  card_detail,
  salesMan,
  acc_code,
  bill_no,
  headerQuoConBy,
  headerQuoConNo,
  mapPaymentMode,
}) {
  const totalItemCount = cart.length;

  const totalAmountBeforeDiscount = cart.reduce((sum, i) => sum + (i.amount), 0);
  const isDeliveryAllowed = window.companyConfigurations?.pos?.delivery_charges_allowed !== false;
  const isTaxAllowed = window.companyConfigurations?.pos?.tax_charges_allowed !== false;
  const isMscAllowed = window.companyConfigurations?.pos?.msc_charges_allowed !== false;

  const validDeliveryCharges = isDeliveryAllowed ? Number(deliveryCharges || 0) : 0;
  const validGstPercent = isTaxAllowed ? Number(gstPercent || 0) : 0;
  const validMscCharges = isMscAllowed ? Number(mscCharges || 0) : 0;

  const calculatedDiscountAmount = (totalAmountBeforeDiscount * discountPercent) / 100;
  const taxableAmount = totalAmountBeforeDiscount - calculatedDiscountAmount + validDeliveryCharges;
  const calculatedGstAmount = (taxableAmount * validGstPercent) / 100;
  const calculatedNetTotal = taxableAmount + calculatedGstAmount + validMscCharges;

  const changeAmount = receivedAmount - calculatedNetTotal;
  let header_cash_paid = 0;
  let header_bank_paid = 0;

  if (Payment_method === 'dual') {
    header_cash_paid = receivedAmount;
    header_bank_paid = calculatedNetTotal - receivedAmount;
  } else if (Payment_method === 'cash') {
    header_cash_paid = receivedAmount;
  } else if (Payment_method === 'card') {
    header_bank_paid = receivedAmount;
  }

  const payload = {
    // Header Totals Mapping
    header_total_items: totalItemCount,
    header_item_total: totalAmountBeforeDiscount,
    header_discount_percent: discountPercent,
    header_discount_amount: calculatedDiscountAmount,
    header_delivery_charges: validDeliveryCharges,
    header_gst_percent: validGstPercent,
    header_gst_amount: calculatedGstAmount,
    header_msc_charges: validMscCharges,
    header_net_total: calculatedNetTotal,
    header_remarks: remarks,

    header_acc_code: acc_code,
    salesman: salesMan,
    // Header Payment Mapping
    header_payment_mode: mapPaymentMode(Payment_method),
    header_bank_paid: header_bank_paid,
    header_cash_paid: header_cash_paid,
    header_card_last4: (Payment_method === "card" || Payment_method === 'dual') && card_detail ? card_detail.slice(-4) : "",
    header_total_paid: Payment_method === 'dual' ? header_bank_paid + header_cash_paid : receivedAmount,
    header_change_amount: changeAmount > 0 ? changeAmount : 0,

    header_quo_con_by: headerQuoConBy,
    header_quo_con_no: Number(headerQuoConNo),

    // Row-level Items Mapping
    items: cart.map((i) => {
      // Calculate packaging quantity details (carton packing, dozen packing, etc.) dynamically based on qtyFactors
      const factor = i.qtyFactors && i.qtyFactors[i.packing_mode] ? i.qtyFactors[i.packing_mode] : 12;
      const uom = i.uoms && i.uoms[i.packing_mode] ? i.uoms[i.packing_mode] : null;
      let packQty = factor;

      const isRowDiscountAllowed = window.companyConfigurations?.pos?.row_discount_allowed !== false;
      return {
        inv_id: i.id,
        prod_name: i.product_description,
        product_name_ur: i.prod_name_ur || "",
        qty: i.qty,
        rate: i.rate,
        packing_mode: i.packing_mode || 1,
        uom: uom,
        pack_qty: Number(packQty.toFixed(3)),
        row_discount_percent: isRowDiscountAllowed ? (i.discount_percent_per_item || 0) : 0,
        row_discount_amount: isRowDiscountAllowed ? (i.discount || 0) : 0,
        row_net_total: i.amount || 0,
        row_notes: i.row_notes || "",
        row_old_total_base_qty: i.row_old_total_base_qty || 0,
      };
    }),
  };

  if (bill_no) {
    payload.bill_no = bill_no;
  }

  return payload;
}