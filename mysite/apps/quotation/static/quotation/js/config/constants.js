/* ══════════════════════════════════════════════════════
   POS Field and Packing Mode Mapping Configuration
   ══════════════════════════════════════════════════════ */

export const POS_MAPPING = {
  // Mapping of inventory model fields to UI properties
  product: {
    inv_id: "inv_id",
    prod_name: "prod_name",
    barcode: "barcode",
    manualbc: "manualbc",
    category: "category",
  
  },

  // Packing mode mappings (1=base, 2=carton, 3=dzn, 4=wholesale)
  packingModes: {
    1: {
      id: 1,
      name: "base",
      label: "Base / Retail",
      priceField: "base_price",
      uom: "base_uom_name",
      discField: "base_disc_per",
      qtyFactorField: null, // Factor is 1
      defaultFactor: 1
    },
    2: {
      id: 2,
      name: "carton",
      label: "Carton",
      priceField: "carton_price",
      uom: "carton_uom_name",
      discField: "carton_disc_per",
      qtyFactorField: "carton_qty",
      defaultFactor: 12
    },
    3: {
      id: 3,
      name: "dzn",
      label: "Dozen",
      priceField: "dzn_price",
      uom: "dzn_uom_name",
      discField: "dzn_disc_per",
      qtyFactorField: "dzn_qty",
      defaultFactor: 12
    },
    4: {
      id: 4,
      name: "wholesale",
      label: "Wholesale",
      priceField: "ws_price",
      discField: "ws_disc_per",
      qtyFactorField: null, // Factor is 1
      defaultFactor: 1
    }
  },

  // Reverse mapping for HTML radio buttons (radio value to packing mode ID)
  radioValueToModeId: {
    "base": 1,
    "carton": 2,
    "dzn": 3,
    "wholesale": 4
  },
  
  // Mode ID to radio value
  modeIdToRadioValue: {
    1: "base",
    2: "carton",
    3: "dzn",
    4: "wholesale"
  }
};

window.POS_MAPPING = POS_MAPPING;



