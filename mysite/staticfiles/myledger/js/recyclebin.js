
// async function saveUpdateDynamicVoucher() {
//     const date = datefield.value;
//     const voucherType = document.getElementById('dvm_hidden_voucher_type_value').value;
//     const bank = banksCombobox.value;
//     const remarks = document.getElementById('dvm_remarks_in_modal').value;
//     let payload;
//     const dvTableBody = document.querySelectorAll('.dv-table-wrapper tbody tr');
//     let listOfVoucherLines = [];
//     dvTableBody.forEach(row => {
//         const cell = row.cells;
//         // console.log(cell,'cell');
//         // console.log(cell[0].value !== undefined && cell[5].value !== undefined && cell[0].value !== null && cell[5].value !== null);
//         if (cell[0].firstElementChild.value !== "" && cell[5].firstElementChild.value !== "0.00" && cell[0].firstElementChild.value !== null && cell[5].firstElementChild.value !== null) {
//             listOfVoucherLines.push({
//                 "accCode": cell[0].firstElementChild.value,
//                 "head": cell[1].firstElementChild.value,
//                 "notes": cell[2].firstElementChild.value,
//                 "receiptNo": cell[3].firstElementChild.value,
//                 "chqNo": cell[4].firstElementChild.value,
//                 "amount": cell[5].firstElementChild.value
//             });
//         }
//     });

//     console.log(listOfVoucherLines, 'listOfVoucherLines');


//     if (listOfVoucherLines && listOfVoucherLines?.length > 0) {

//         if (voucherType == "CP" || voucherType == "CR") {
//             if (date === '') {
//                 alert('Please select a date');
//                 return;
//             }
//             payload = {
//                 "date": date,
//                 "voucherType": voucherType,
//                 "listOfVoucherLines": listOfVoucherLines,
//                 "remarks": remarks
//             }
//         }
//         else if (voucherType == "BP" || voucherType == "BR") {
//             if (date === '') {
//                 alert('Please select a date');
//                 return;
//             }
//             if (bank === '') {
//                 alert('Please select a bank');
//                 return;
//             }
//             payload = {
//                 "date": date,
//                 "voucherType": voucherType,
//                 "bank": bank,
//                 "listOfVoucherLines": listOfVoucherLines,
//                 "remarks": remarks
//             }
//         }
//         else if (voucherType == "ADJ") {
//             if (date === '') {
//                 alert('Please select a date');
//                 return;
//             }
//             if (transactionType === '') {
//                 alert('Please select a transaction type');
//                 return;
//             }
//             payload = {
//                 "date": date,
//                 "voucherType": voucherType,
//                 "transactionType": document.getElementById('dvm_transaction_type_value').value,
//                 "listOfVoucherLines": listOfVoucherLines,
//                 "remarks": remarks
//             }
//         } else {
//             return alert("Please Select a Voucher Type");
//         }
//     } else {
//         return alert("Please Enter At Least One Voucher Line");
//     }

//     const save_dynamic_voucher_response = await myLedgerHelpers.saveUpdateDynamicVoucher(payload);
//     console.log(save_dynamic_voucher_response, 'save_dynamic_voucher_response');
//     if (save_dynamic_voucher_response.success) {
//         alert(save_dynamic_voucher_response.message);
//         // closeDynamicVoucherModal();
//     } else {
//         alert(save_dynamic_voucher_response.message);
//     }

// }

