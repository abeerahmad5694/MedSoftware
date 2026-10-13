from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa # type: ignore
from apps.myledger.models import Gledg
from apps.reports.views.daybook import data_colomun
from datetime import date

def render_to_pdf(template_src,context={}):
    template = get_template(template_src)
    html = template.render(context)
    response = HttpResponse(content_type = 'application/pdf')
    response['Content-Disposition'] = f'inline; filename="daybook.pdf"'
    pisa_status = pisa.CreatePDF(html,dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation error <pre>' + html + '</pre>') 
    
    return response



def generate_daybook_pdf(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user = request.user
    data , columns ,summary= data_colomun(Gledg,date_from,date_to,user)

    context = {
        'data': data,
        'columns': columns,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render_to_pdf('All_Reports/daybook_pdf.html', context)


# from django.conf import settings
# import base64
# import os

# def daybook_pdf(request):
#     ...

#     logo_path = os.path.join(settings.BASE_DIR, 'static/company/logo.png')
#     with open(logo_path, 'rb') as f:
#         logo_base64 = base64.b64encode(f.read()).decode()

#     context = {
#         'data': data,
#         'columns': columns,
#         'date_from': date_from,
#         'date_to': date_to,
#         'logo': logo_base64,
#     }

#     template = get_template('All_Reports/daybook_pdf.html')
#     html = template.render(context)

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = 'inline; filename="daybook.pdf"'
#     pisa.CreatePDF(html, dest=response)
#     return response
