from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from apps.configuration.models import DefaultAccounts, Company, Branch
from apps.configuration.selectors import get_default_accounts, DEFAULT_ACCOUNTS_DATA
from apps.myaccounts.models import Accounts


@login_required

def default_accounts_view(request):
    can_view, message = get_user_perms(request, 'configure_system')
    if not can_view:
        return redirect('page_not_found')

    user_profile = getattr(request.user, 'userprofile', None)

    # Determine company and branch
    if request.user.is_superuser:
        company_id = request.GET.get('company')
        branch_id = request.GET.get('branch')

        if company_id:
            company = Company.objects.filter(id=company_id).first() or (user_profile.company if user_profile else Company.objects.first())
        else:
            company = (user_profile.company if user_profile else Company.objects.first())

        if branch_id:
            branch = Branch.objects.filter(id=branch_id, company=company).first() or (user_profile.branch if user_profile else Branch.objects.filter(company=company).first())
        else:
            branch = (user_profile.branch if user_profile else Branch.objects.filter(company=company).first())
    else:
        company = getattr(user_profile, 'company', None) or Company.objects.first()
        branch = getattr(user_profile, 'branch', None) or Branch.objects.filter(company=company).first()

    if not company or not branch:
        messages.error(request, "Company or Branch not identified. Please configure companies and branches first.")
        return redirect('company')

    # Get or initialize DefaultAccounts instance
    acc_config_instance = DefaultAccounts.objects.filter(company=company, branch=branch).first()

    if request.method == 'POST':
        # Collect all submitted account codes
        accounts_payload = {}
        for key in DEFAULT_ACCOUNTS_DATA.keys():
            val = request.POST.get(key)
            if val:
                try:
                    accounts_payload[key] = int(val)
                except ValueError:
                    accounts_payload[key] = val

        # Save or update instance
        if not acc_config_instance:
            acc_config_instance = DefaultAccounts(company=company, branch=branch)

        acc_config_instance.accounts_data = accounts_payload
        acc_config_instance.save()

        # Handle "Apply to All Branches"
        if request.POST.get('all_branches'):
            all_branches = Branch.objects.filter(company=company)
            for b in all_branches:
                DefaultAccounts.objects.update_or_create(
                    company=company,
                    branch=b,
                    defaults={'accounts_data': accounts_payload}
                )
            messages.success(request, f"Default accounts updated and applied across all branches of {company.name}.")
        else:
            messages.success(request, f"Default accounts successfully updated for branch '{branch.name}'.")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Default accounts saved successfully!'})

        if request.user.is_superuser:
            return redirect(f"{request.path}?company={company.id}&branch={branch.id}")
        return redirect('default_accounts')

    # On GET: load merged data
    merged_accounts, _ = get_default_accounts(company.id if company else None, branch.id if branch else None)

    # Fetch accounts list for select dropdowns
    all_accounts = list(Accounts.objects.filter(LEVEL= 4,TYPE='Detail').order_by('ACC_CODE'))
    companies = list(Company.objects.all().order_by('name')) if request.user.is_superuser else [company]
    branches = list(Branch.objects.filter(company=company).order_by('name')) if company else []

    context = {
        'company': company,
        'branch': branch,
        'companies': companies,
        'branches': branches,
        'accounts_data': merged_accounts,
        'all_accounts': all_accounts,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'configuration/default_accounts.html', context)
