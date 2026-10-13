import pandas as pd
from django.http import HttpResponse
from apps.myledger.models import Gledg
from apps.reports.views.daybook import data_colomun

def render_to_excell(date_from,date_to,data,column_heading=[]):
    df = pd.DataFrame(list(data))
    df.columns = column_heading
    response = HttpResponse(content_type ='text/csv')
    response["Content_Deposition"] = 'attachement; filname="report.csv"'
    df.to_csv(response,index=False)
    return response



def generate_daybook_excell(request):
    
    user = request.user
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    data ,columns,summary = data_colomun(Gledg,date_from,date_to,user)
    column_heading = [row['label'] for row in columns]
    if not data:
        return HttpResponse('No Data Found')
    return render_to_excell(date_from , date_to , data , column_heading)