export const Helpers={

    nextAccountUrl:`/myaccounts/api/get-next-account-code/`,

    getNextAccountCode:async function(parentCode,level){
        const payload = {
            parent_acc_code:parentCode,
            level:level,
        }
        const res = await fetch(this.nextAccountUrl,{
            method:"POST",
            headers:{
                "Content-Type": "application/json",
                "X-CSRFToken": window.getCSRFToken(),
            },
            body:JSON.stringify(payload),
        })
        if(!res.ok){
            console.log('There is any error')
            return 
        }
        const data = await res.json()
        return data
    },
    
    getClassFieldAndAccountTypeByStartingCode:function(accCode,level){
        const DETAIL_LEVEL = 4;
        let classField,accType
        if (level == DETAIL_LEVEL) {
            accType = 'Detail';
        } else {
            accType = 'Group';
        }
        if (String(accCode).startsWith('1')) {
            classField = 'Assets';
        }
        else if (String(accCode).startsWith('2')) {
            classField = 'Liability';
        }
        else if (String(accCode).startsWith('3')) {
            classField = 'Expanse';
        }
        else if (String(accCode).startsWith('4')) {
            classField = 'Income';
        }
        else {
            classField = 'Assets';
        }
        return {
            classField,
            accType
        }
    },


    // getCookie:function (name) {
    //     let cookieValue = null;
    //     if (document.cookie && document.cookie !== '') {
    //         const cookies = document.cookie.split(';');
    //         for (let i = 0; i < cookies.length; i++) {
    //             const cookie = cookies[i].trim();
    //             if (cookie.substring(0, name.length + 1) === (name + '=')) {
    //                 cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
    //                 break;
    //             }
    //         }
    //     }
    //     return cookieValue;
// }

}


