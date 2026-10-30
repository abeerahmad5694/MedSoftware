



function fetch_full_model(app_label, model_name){
    const url = `/${app_constants.fetch_full_model_api}/${app_label}/${model_name}/`;
    return fetch(url)
    .then(res=>{
        if(res.ok){
            return res.json();
        }
        throw new Error('Network response was not ok');
    })
    .then(data=>{
        if(data.success)
            return data.results;
        throw new Error(data.error || 'Error fetching data');
    })
    .catch(err=>{
        console.error('Fetch Full Model Error:', err);
        throw err;
    });
}

