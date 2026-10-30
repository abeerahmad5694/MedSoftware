

export async function deleteBill(bill_no, pur_inv) {
  if (!bill_no) return alert("No bill to delete", "error");
  if (!pur_inv) return alert("No purchase invoice to delete", "error");
  if (confirm("Are you sure you want to delete this bill?")) {
    try {
      const res = await fetch(
        window.app_constants.delete_sale_bill_api
          ? window.app_constants.delete_sale_bill_api +
              `${encodeURIComponent(pur_inv)}` +
              `${encodeURIComponent(bill_no)}`
          : `/sale/api/delete_sale_bill/${encodeURIComponent(pur_inv)}/${encodeURIComponent(bill_no)}/`,
      );
      if (!res.ok) return alert("Network error deleting bildl", "error");
      const data = await res.json();
      if (!data.success) return alert(data.message);
      alert(data.message, "success");

      // New_bill();
    } catch (e) {
      alert(e.message, "error");
    }
  }
}
