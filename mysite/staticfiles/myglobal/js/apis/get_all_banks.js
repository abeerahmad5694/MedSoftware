
export async function get_all_banks(){
    const response = await fetch(window.app_constants.get_all_banks_api || '/myledger/api/get_banks/',);
    const data = await response.json();
    if (data.success) {
      return data.data;
    } else {
      console.error(data.error);
      return null;
    }
}