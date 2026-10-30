
  const ReceiptModal = (function () {
    let _receiptData = null;
    let _isQzConnected = false;
    let _qzPrinter = null; // Store the selected printer

    // --- Helper Functions ---

    // Converts base64 to ArrayBuffer for QZ-Tray
    const _base64ToArrayBuffer = (base64) => {
      const binaryString = window.atob(base64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return bytes.buffer;
    };

    /**
     * Initializes and connects to the QZ-Tray service.
     */
    const _connectQz = () => {
      // ✅ Prevent reconnect if already active
      if (qz.websocket.isActive()) {
        _isQzConnected = true;
        return Promise.resolve(true);
      }

      if (typeof qz === "undefined" || !qz.websocket) {
        console.error(
          "QZ-Tray client script is not loaded. Printing is disabled."
        );
        return Promise.reject(new Error("QZ-Tray not available."));
      }

      return qz.websocket
        .connect()
        .then(() => {
          _isQzConnected = true;
          console.log("QZ-Tray connected successfully.");
          return qz.printers.getDefault().then((printer) => {
            _qzPrinter = printer;
            console.log("Default printer selected:", _qzPrinter);
            return true;
          });
        })
        .catch((err) => {
          _isQzConnected = false;
          console.error("QZ-Tray connection failed:", err);
          return false;
        });
    };


    const _generateReceiptHTML = (data) => {
      const itemsList = data.items
        .map(
          (item) => `
              <tr class="item-row">
                  
                  <td>${item.description}</td>
                  <td>${item.qty} </td>
                  <td class="text-right">${item.price.toFixed(2)}</td>
                  <td class="text-right">${item.amount.toFixed(2)}</td>
              </tr>
          `
        )
        .join("");

      const subtotal = data.total ;
      const change = data.received_amount - (data.net_total || data.total)
      return `
              <div class="receipt-header">
                  <div class="logo">
                      ${
                        data.logo
                          ? `<img src="${data.logo?data.logo:''}" alt="Logo" style="max-width:80px; max-height:80px;"  />`
                          : ''
                      }
                  </div>
                  <h2>${data.shop?data.shop:''}</h2>
                  <h3>${data.header_text?data.header_text:''}</h3>
                  <p>Date: ${data.date}</p>
                  <p>Bill No: <strong>${data.voucher_no}</strong></p>
                  <hr>
              </div>
              
              <div class="receipt-body">
                  <table class="items-table">
                      <thead>
                          <tr class="item-header">
                              <th>Item</th>
                              <th>Qty</th>
                              <th class="text-right">Rate</th>
                              <th class="text-right">Amount</th>
                          </tr>
                      </thead>
                      <tbody>
                          ${itemsList}
                      </tbody>
                  </table>
              </div>

              <div class="receipt-summary">
                  <hr>
                  <div class="summary-line">
                      <span>Subtotal:</span>
                      <span class="text-right">${subtotal.toFixed(2)}</span>
                  </div>
                  ${
                    data.discount
                      ? `
                      <div class="summary-line discount">
                          <span>Discount (${data.discountPercent}%):</span>
                          <span class="text-right">-${data.discount.toFixed(
                            2
                          )}</span>
                      </div>
                  `
                      : ""
                  }
                  ${
                    data.delivery_charges > 0
                      ? `
                      <div class="summary-line delivery">
                          <span>Delivery Charges:</span>
                          <span class="text-right">${data.delivery_charges.toFixed(
                            2
                          )}</span>
                      </div>
                  `
                      : ""
                  }
                  <hr>
                  <div class="summary-line total">
                      <strong>Net Total:</strong>
                      <strong class="text-right">${
                        data.net_total
                          ? data.net_total.toFixed(2)
                          : data.total.toFixed(2)
                      }</strong>
                  </div>
                  <div class="summary-line received">
                      <span>Received Amount:</span>
                      <span class="text-right">${data.received_amount.toFixed(
                        2
                      )}</span>
                  </div>
                  ${
                    change >= 1
                      ? `
                          <div class="summary-line change">
                            <strong>Change/Balance:</strong>
                            <strong class="text-right">${change.toFixed(
                              2
                            )}</strong>
                          </div>`
                      : ""
                  }
                  <hr>
                  <p> <strong>${
                    data.payment_mode == "card" ? "Payment: Card" : ""
                  }</strong></p>
                  ${
                    data.remarks
                      ? `<p class="remarks">Remarks: ${data.remarks}</p>`
                      : ""
                  }
              </div>

              <div class="receipt-footer">
                  <p>${data.footer_text?data.footer_text:''}</p>
              </div>
          `;
    };

    /**
     * Handles the actual QZ-Tray printing command.
     */
    const _sendPrintCommand = async (printerName, data) => {
      if (!_isQzConnected || !printerName)
        return console.error("Printer not ready");

      // const escpos = [
      //   "\x1B\x40", // init
      //   "\x1B\x61\x01", // center
      //   data.logo
      //     ? await qz.appendImage({
      //         data: data.logo,
      //         options: { language: "ESCPOS" },
      //       })
      //     : "",
      //   `${data.header_text}\n`,
      //   "\x1B\x61\x00", // left
      //   `Date: ${data.date}\nVoucher: ${data.voucher_no}\n-----------------------------\n`,
      //   (data.items || []).map(
      //     (i) =>
      //       `${i.qty || 0} x ${i.description || ""}\t${(i.amount || 0).toFixed(
      //         2
      //       )}\n`
      //   ),
      //   `Total: ${((data.net_total ?? data.total) || 0).toFixed(2)}\n`,
      //   data.discount > 0 ? `Discount: ${(data.discount || 0).toFixed(2)}\n` : "",
      //   data.delivery_charges > 0
      //     ? `Delivery: ${(data.delivery_charges || 0).toFixed(2)}\n`
      //     : "",
      //   `Received: ${(data.received_amount || 0).toFixed(2)}\n`,
      //   data.received_amount - (data.net_total || data.total) !== 0
      //     ? `Change: ${(
      //         data.received_amount - (data.net_total || data.total)
      //       ).toFixed(2)}\n`
      //     : "",
      //   "\x1B\x61\x01", // center
      //   `${data.footer_text}\n\n`,
      //   "\x1D\x56\x41", // cut
      // ];
      

      const escpos = [
        "\x1B\x40", // Init
        "\x1B\x61\x01", // Center

        // Header Logo
        ...(data.logo
          ? [
              await qz.appendImage({
                data: data.logo,
                options: { language: "ESCPOS" },
              }),
            ]
          : []),

        // Header Texts
        ...(data.shop ? [`${data.shop}\n`] : []),
        ...(data.header_text ? [`${data.header_text}\n`] : []),

        "\x1B\x61\x00", // Left align
        `Date: ${data.date}  Bill NO: ${data.voucher_no}\n`,
        "-------------------------------\n",

        // Table headers
        "Qty  Item                 Rate    Amount\n",
        "---------------------------------------\n",

        // Items
        ...(data.items || []).map((i) => {
          const qty = i.qty.toString().padEnd(3, " ");
          const desc = i.description.padEnd(20, " ");
          const rate = (i.price || 0).toFixed(2).padStart(6, " ");
          const amount = (i.amount || 0).toFixed(2).padStart(7, " ");
          return `${qty} ${desc} ${rate} ${amount}\n`;
        }),

        "---------------------------------------\n",

        // Summary
        `Subtotal: ${(data.total || 0).toFixed(2).padStart(10, " ")}\n`,

        ...(data.discount > 0
          ? [
              `Discount (${
                data.discountPercent || 0
              }%): -${data.discount.toFixed(2)}\n`,
            ]
          : []),

        ...(data.delivery_charges > 0
          ? [`Delivery Charges: ${data.delivery_charges.toFixed(2)}\n`]
          : []),

        `Net Total: ${(data.net_total || data.total || 0)
          .toFixed(2)
          .padStart(10, " ")}\n`,
        `Received: ${(data.received_amount || 0)
          .toFixed(2)
          .padStart(10, " ")}\n`,

        ...(data.received_amount - (data.net_total || data.total) !== 0
          ? [
              `Change: ${(data.received_amount - (data.net_total || data.total))
                .toFixed(2)
                .padStart(10, " ")}\n`,
            ]
          : []),

        ...(data.payment_mode === "card" ? [`Payment: Card\n`] : []),
        ...(data.remarks ? [`Remarks: ${data.remarks}\n`] : []),

        "\x1B\x61\x01", // Center footer
        ...(data.footer_text ? [`${data.footer_text}\n\n`] : []),

        "\x1D\x56\x41", // Cut
      ];

      const config = qz.configs.create(printerName, { language: "ESCPOS" });
      qz.print(config, [
        { type: "raw", format: "command", data: escpos.join("") },
      ]).catch((e) => console.error("Print failed:", e));
    };

    qz.security.setCertificatePromise((resolve) =>
      fetch("/static/digital-certificate.txt")
        .then((res) => res.text())
        .then(resolve)
    );

    qz.security.setSignaturePromise(function (toSign) {
      return function (resolve, reject) {
        fetch(`/sale/qz-sign?request=${encodeURIComponent(toSign)}`)
          .then((res) => res.json())
          .then((data) => resolve(data.signature))
          .catch(reject);
      };
    });

    // --- Public Interface ---

    return {
  
      open: function (data) {
        _receiptData = data;
        const modal = document.getElementById("receipt-modal");
        const content = document.getElementById("receipt-modal-content");

        if (!modal || !content) {
          console.error("Receipt modal DOM elements not found.");
          return;
        }

        content.innerHTML = _generateReceiptHTML(data);
        modal.style.display = "flex";
      },

      /**
       * Closes the receipt modal preview.
       */
      close: function () {
        const modal = document.getElementById("receipt-modal");
        if (modal) {
          modal.style.display = "none";
        }
      },

      print: async function (data) {
        _receiptData = data;

        const content = _generateReceiptHTML(data);

        // 1. Ensure QZ-Tray connection
        const connected = await _connectQz();

        if (connected && _qzPrinter) {
          // 2. Send command
          _sendPrintCommand(_qzPrinter, content);
        } else {
          console.warn(
            "Could not print. QZ-Tray connection or printer selection failed."
          );
          // Fallback to browser print if QZ-Tray fails
          window.print();
        }
      },
    };
  })();

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" || e.key==='Enter') {
      e.preventDefault()
      ReceiptModal.close();
      
    }
  });
  // Attach event listeners to close the modal when DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("receipt-modal");
    const closeBtn = document.getElementById("receipt-close-btn");

    if (closeBtn) {
      closeBtn.onclick = ReceiptModal.close;
    }

    // Close modal if user clicks outside of the content area
    if (modal) {
      modal.onclick = (event) => {
        if (event.target === modal) {
          ReceiptModal.close();
        }
      };
    }
  });
  // document.addEventListener("DOMContentLoaded", () => {
  //   const modal = document.getElementById("receipt-modal");
  //   const closeBtn = document.getElementById("receipt-close-btn");

  //   if (closeBtn) closeBtn.onclick = ReceiptModal.close;

  //   if (modal) {
  //     modal.onclick = (event) => {
  //       if (event.target === modal) ReceiptModal.close();
  //     };
  //   }

  //   // ✅ Raw print simulation without a printer
  //   if (typeof qz !== "undefined" && qz.websocket) {
  //     qz.websocket.connect().then(() => {
  //       const cfg = qz.configs.create(null); // no printer = test mode
  //       const data = [
  //         { type: "raw", format: "plain", data: "TEST RAW PRINT\n\n\n" },
  //       ];
  //       qz.print(cfg, data)
  //         .then(() => console.log("✅ Raw print simulated"))
  //         .catch((e) => console.error("❌ Raw print failed", e));
  //     });
  //   }
  // });


  export {ReceiptModal}













  
// /**
//  * ReceiptModal Module
//  * Manages the display and raw ESC/POS printing of receipts using QZ-Tray.
//  * * NOTE ON ERROR: qz.appendImage has been commented out to fix 'qz.appendImage is not a function' 
//  * error, which occurs when using QZ-Tray versions older than 2.1.
//  * For logo printing to work, please update QZ-Tray, then uncomment the logo section in 
//  * _sendPrintCommand.
//  */
// const ReceiptModal = (function () {
//     let _receiptData = null;
//     let _isQzConnected = false;
//     let _qzPrinter = null; // Store the selected printer

//     // --- Helper Functions ---

//     /**
//      * Initializes and connects to the QZ-Tray service.
//      */
//     const _connectQz = () => {
//         // Prevent reconnect if already active
//         if (qz.websocket.isActive()) {
//             _isQzConnected = true;
//             return Promise.resolve(true);
//         }

//         if (typeof qz === "undefined" || !qz.websocket) {
//             console.error(
//                 "QZ-Tray client script is not loaded. Printing is disabled."
//             );
//             return Promise.reject(new Error("QZ-Tray not available."));
//         }

//         return qz.websocket
//             .connect()
//             .then(() => {
//                 _isQzConnected = true;
//                 console.log("QZ-Tray connected successfully.");
//                 // Ensure we get the default printer after a successful connection
//                 return qz.printers.getDefault();
//             })
//             .then((printer) => {
//                 _qzPrinter = printer;
//                 console.log("Default printer selected:", _qzPrinter);
//                 return true;
//             })
//             .catch((err) => {
//                 _isQzConnected = false;
//                 _qzPrinter = null;
//                 console.error("QZ-Tray connection failed:", err);
//                 return false;
//             });
//     };

//     /**
//      * Generates the HTML preview for the modal.
//      */
//     const _generateReceiptHTML = (data) => {
//         // Fallback for data property access
//         const items = data.items || [];
//         const total = data.total || 0;
//         const netTotal = data.net_total || total;
//         const receivedAmount = data.received_amount || 0;
//         const change = receivedAmount - netTotal;

//         const itemsList = items
//             .map(
//                 (item) => `
//                     <tr class="item-row">
//                         <td>${item.qty} x</td>
//                         <td>${item.description}</td>
//                         <td class="text-right">${(item.price || 0).toFixed(2)}</td>
//                         <td class="text-right">${(item.amount || 0).toFixed(2)}</td>
//                     </tr>
//                 `
//             )
//             .join("");

//         return `
//                 <div class="receipt-header">
//                     <div class="logo">
//                         ${
//                             data.logo
//                                 ? `<img src="${data.logo}" alt="Logo" style="max-width:80px; max-height:80px;" />`
//                                 : ''
//                         }
//                     </div>
//                     <h2>${data.shop || ''}</h2>
//                     <h3>${data.header_text || ''}</h3>
//                     <p>Date: ${data.date}</p>
//                     <p>Bill No: <strong>${data.voucher_no}</strong></p>
//                     <hr>
//                 </div>
                
//                 <div class="receipt-body">
//                     <table class="items-table">
//                         <thead>
//                             <tr class="item-header">
//                                 <th>Qty</th>
//                                 <th>Item</th>
//                                 <th class="text-right">Rate</th>
//                                 <th class="text-right">Amount</th>
//                             </tr>
//                         </thead>
//                         <tbody>
//                             ${itemsList}
//                         </tbody>
//                     </table>
//                 </div>

//                 <div class="receipt-summary">
//                     <hr>
//                     <div class="summary-line">
//                         <span>Subtotal:</span>
//                         <span class="text-right">${total.toFixed(2)}</span>
//                     </div>
//                     ${
//                         data.discount && data.discount > 0
//                             ? `
//                             <div class="summary-line discount">
//                                 <span>Discount (${data.discountPercent || 0}%):</span>
//                                 <span class="text-right">-${data.discount.toFixed(
//                                     2
//                                 )}</span>
//                             </div>
//                         `
//                             : ""
//                     }
//                     ${
//                         data.delivery_charges && data.delivery_charges > 0
//                             ? `
//                             <div class="summary-line delivery">
//                                 <span>Delivery Charges:</span>
//                                 <span class="text-right">${data.delivery_charges.toFixed(
//                                     2
//                                 )}</span>
//                             </div>
//                         `
//                             : ""
//                     }
//                     <hr>
//                     <div class="summary-line total">
//                         <strong>Net Total:</strong>
//                         <strong class="text-right">${netTotal.toFixed(2)}</strong>
//                     </div>
//                     <div class="summary-line received">
//                         <span>Received Amount:</span>
//                         <span class="text-right">${receivedAmount.toFixed(
//                             2
//                         )}</span>
//                     </div>
//                     ${
//                         change >= 0.01 // Only show change if relevant
//                             ? `
//                                 <div class="summary-line change">
//                                     <strong>Change/Balance:</strong>
//                                     <strong class="text-right">${change.toFixed(
//                                         2
//                                     )}</strong>
//                                 </div>`
//                             : ""
//                     }
//                     <hr>
//                     <p> <strong>${
//                         data.payment_mode === "card" ? "Payment: Card" : ""
//                     }</strong></p>
//                     ${
//                         data.remarks
//                             ? `<p class="remarks">Remarks: ${data.remarks}</p>`
//                             : ""
//                     }
//                 </div>

//                 <div class="receipt-footer">
//                     <p>${data.footer_text || ''}</p>
//                 </div>
//             `;
//     };

//     /**
//      * Handles the actual QZ-Tray printing command (ESC/POS).
//      */
//     const _sendPrintCommand = async (printerName, data) => {
//         if (!_isQzConnected || !printerName)
//             return console.error("Printer not ready or QZ-Tray not connected.");

//         const netTotal = data.net_total || data.total || 0;
//         const receivedAmount = data.received_amount || 0;
//         const change = receivedAmount - netTotal;

//         const escpos = [
//             "\x1B\x40", // Init
//             "\x1B\x61\x01", // Center align

//             // =========================================================================
//             // NOTE: The following logo section is commented out because it was causing 
//             // the 'qz.appendImage is not a function' error in older QZ-Tray versions.
//             // If you update QZ-Tray to 2.1+, you can uncomment this block.
//             // -------------------------------------------------------------------------
//             // ...(data.logo
//             //     ? [
//             //         // Await the async image conversion
//             //         await qz.appendImage({
//             //             data: data.logo,
//             //             options: { language: "ESCPOS", dotDensity: 'single' }, 
//             //         }),
//             //       ]
//             //     : []),
//             // =========================================================================

//             // Header Texts
//             ...(data.shop ? [`${data.shop}\n`] : []),
//             ...(data.header_text ? [`${data.header_text}\n`] : []),
            
//             "\x1B\x61\x00", // Left align
//             `Date: ${data.date} \tBill NO: ${data.voucher_no}\n`,
//             "-------------------------------\n",

//             // Items 
//             `Qty\tItem\t\t\tAmount\n`,
//             "-------------------------------\n", 
            
//             // Dynamically generate item lines
//             ...(data.items || []).map((i) => {
//                 // Use a simple tab separation for ESC/POS compatibility
//                 return `${i.qty} ${i.description || ""}\t\t${(i.amount || 0).toFixed(2)}\n`;
//             }),

//             "-------------------------------\n",

//             // Summary (Using right alignment for numbers)
//             `Subtotal:\t\t\t${(data.total || 0).toFixed(2)}\n`,

//             ...(data.discount && data.discount > 0
//                 ? [
//                       `Discount (${
//                           data.discountPercent || 0
//                       }%):\t\t-${data.discount.toFixed(2)}\n`,
//                   ]
//                 : []),

//             ...(data.delivery_charges && data.delivery_charges > 0
//                 ? [`Delivery Charges:\t\t${data.delivery_charges.toFixed(2)}\n`]
//                 : []),
            
//             // Total is often highlighted
//             "\x1B\x21\x30", // Double height and double width
//             `NET TOTAL:\t\t\t${netTotal.toFixed(2)}\n`,
//             "\x1B\x21\x00", // Back to normal font

//             `Received:\t\t\t${receivedAmount.toFixed(2)}\n`,

//             ...(change > 0.01 // Only print change if it exists
//                 ? [
//                       `Change:\t\t\t\t${change.toFixed(2)}\n`,
//                   ]
//                 : []),
            
//             "-------------------------------\n",

//             ...(data.payment_mode === "card" ? [`Payment: Card\n`] : []),
//             ...(data.remarks ? [`Remarks: ${data.remarks}\n`] : []),

//             "\x1B\x61\x01", // Center footer
//             ...(data.footer_text ? [`\n${data.footer_text}\n\n`] : []),

//             "\x1D\x56\x41", // Cut
//         ];
        
//         // Join all parts into a single command string
//         const finalEscposCommand = escpos.join("");
//         // Updated logging to clarify this is data preparation, not the actual print action.
//         console.log("QZ-Tray Raw ESC/POS data prepared."); 

//         const config = qz.configs.create(printerName, { language: "ESCPOS" });
        
//         // This is the command that sends the data to the QZ-Tray application, 
//         // which then routes it to the physical printer.
//         console.log(`Sending print job to default thermal printer: ${printerName}`);
        
//         qz.print(config, [
//             { type: "raw", format: "command", data: finalEscposCommand },
//         ]).catch((e) => console.error("Print failed:", e));
//     };

//     // --- QZ-Tray Security Configuration (Required) ---

//     // Note: The URLs below assume the certificate and signature service are hosted 
//     // at these paths relative to your application's root.
//     qz.security.setCertificatePromise((resolve) =>
//         fetch("/static/digital-certificate.txt")
//             .then((res) => res.text())
//             .then(resolve)
//     );

//     qz.security.setSignaturePromise(function (toSign) {
//         return function (resolve, reject) {
//             fetch(`/sale/qz-sign?request=${encodeURIComponent(toSign)}`)
//                 .then((res) => res.json())
//                 .then((data) => resolve(data.signature))
//                 .catch(reject);
//         };
//     });

//     // --- Public Interface ---

//     return {
 
//         open: function (data) {
//             _receiptData = data;
//             const modal = document.getElementById("receipt-modal");
//             const content = document.getElementById("receipt-modal-content");

//             if (!modal || !content) {
//                 console.error("Receipt modal DOM elements not found.");
//                 return;
//             }

//             content.innerHTML = _generateReceiptHTML(data);
//             modal.style.display = "flex";
//         },

//         /**
//          * Closes the receipt modal preview.
//          */
//         close: function () {
//             const modal = document.getElementById("receipt-modal");
//             if (modal) {
//                 modal.style.display = "none";
//             }
//         },

//         /**
//          * Connects to QZ-Tray, selects the default printer, and sends the raw ESC/POS command.
//          */
//         print: async function (data) {
//             // Set data immediately
//             _receiptData = data;

//             // 1. Ensure QZ-Tray connection
//             const connected = await _connectQz();

//             // The _connectQz function already finds the default printer and stores it in _qzPrinter.
//             if (connected && _qzPrinter) {
//                 try {
//                     // 2. Send command to the default printer (_qzPrinter)
//                     await _sendPrintCommand(_qzPrinter, data); 
//                 } catch (e) {
//                     console.error("Error during print command execution:", e);
//                     window.print(); // Fallback
//                 }
//             } else {
//                 console.warn(
//                     "Could not print. QZ-Tray connection or printer selection failed. Falling back to browser print."
//                 );
//                 // Fallback to browser print if QZ-Tray fails
//                 window.print();
//             }
//         },
//     };
// })();

// // --- DOM Event Handlers ---

// document.addEventListener("keydown", (e) => {
//     if (e.key === "Escape" || e.key === 'Enter') {
//         e.preventDefault()
//         ReceiptModal.close();
//     }
// });

// document.addEventListener("DOMContentLoaded", () => {
//     const modal = document.getElementById("receipt-modal");
//     const closeBtn = document.getElementById("receipt-close-btn");

//     if (closeBtn) {
//         closeBtn.onclick = ReceiptModal.close;
//     }

//     // Close modal if user clicks outside of the content area
//     if (modal) {
//         modal.onclick = (event) => {
//             if (event.target === modal) {
//                 ReceiptModal.close();
//             }
//         };
//     }
// });


// export {ReceiptModal}