from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from apps.configuration.forms.company import CompanyForm
from apps.configuration.models import Company , Branch
from django.contrib import messages
from apps.myglobal.services.helpers import DateTimeHelper
from apps.myledger.services.helpers import get_user_perms

@login_required
def company(request):
    can_view, message = get_user_perms(request, 'configure_system')
    if not can_view:
        return redirect('page_not_found')
        
    company = Company.objects.first()
    # print('company',company.created_at)
    # print(DateTimeHelper().get_server_time())
    # print(DateTimeHelper().get_local_time())
    # print(comp.name for comp in Company.objects.all())
    if not company:
        return redirect('inventory')
    form = CompanyForm(instance=company)

    if request.method == 'POST':   
        if request.user.is_superuser:
            form = CompanyForm(request.POST, instance=company ,files=request.FILES)
            if form.is_valid():
                form.save()
                
                if 'same-one-branch' in request.POST:
                    branch = Branch.objects.filter(company=company).first()
                    if branch:
                        branch.name = company.name
                        branch.address = company.address
                        branch.phone1 = company.phone1
                        branch.phone2 = company.phone2
                        branch.email = company.email
                        branch.license_no = company.license_no
                        branch.logo = company.logo
                        branch.save()
                        messages.success(request, 'Branch updated successfully')
                        return redirect('company')
                    else:
                        messages.error(request, 'Branch not found')
                        return redirect('company')  
                return redirect('company')
        else:
            messages.error(request, 'You are not authorized to perform this action')
            return redirect('company')
        
    return render(request, 'configuration/company.html', {'form': form})