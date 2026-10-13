// // Dynamic Multi-Price Loader: If packing mode select was triggered, dynamically adjust the rate value and discount from mapped registry
  // if (this.classList.contains("packing-mode-select")) {
  //   rate = item.prices && item.prices[packingMode] !== undefined ? item.prices[packingMode] : rate;
  //   discountPercent = item.discounts && item.discounts[packingMode] !== undefined ? item.discounts[packingMode] : discountPercent;

  //   row.querySelector(".rate-input").value = rate;
  //   const discPctEl = row.querySelector(".discount_percent_per_item-input");
  //   if (discPctEl) discPctEl.value = discountPercent;
  // }

  // // Update original price index if user manually types in custom rates
  // if (this.classList.contains("rate-input")) {
  //   if (!item.prices) item.prices = {};
  //   item.prices[packingMode] = rate;
  // }

  // // Update original discount index if user manually types custom discounts
  // if (this.classList.contains("discount_percent_per_item-input")) {
  //   if (!item.discounts) item.discounts = {};
  //   const typedDiscPercent = Number(row.querySelector(".discount_percent_per_item-input").value) || 0;
  //   item.discounts[packingMode] = typedDiscPercent;
  //   discountPercent = typedDiscPercent;
  // }