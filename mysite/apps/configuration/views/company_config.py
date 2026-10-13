# import requests_oauthlib
from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from apps.configuration.models import CompanyConfiguration, Branch, Company
from apps.configuration.selectors import get_company_config, get_default_accounts, DEFAULT_CONFIG_DATA


@login_required

def company_config_view(request):
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
        messages.error(request, "Company or Branch not identified.")
        return redirect('company')

    # Get or initialize config instance
    config_instance = CompanyConfiguration.objects.filter(company=company, branch=branch).first()

    if request.method == 'POST':
        # Parse all module settings from POST
        pos_config = {
            'max_row_discount_percent': float(request.POST.get('pos_max_row_discount_percent') or 0),
            'max_row_discount_amount': float(request.POST.get('pos_max_row_discount_amount') or 0),
            'max_total_discount_percent': float(request.POST.get('pos_max_total_discount_percent') or 0),
            'row_discount_allowed': request.POST.get('pos_row_discount_allowed') == 'on',
            'delivery_charges_allowed': request.POST.get('pos_delivery_charges_allowed') == 'on',
            'tax_charges_allowed': request.POST.get('pos_tax_charges_allowed') == 'on',
            'msc_charges_allowed': request.POST.get('pos_msc_charges_allowed') == 'on',
            'total_gst_percent': float(request.POST.get('pos_total_gst_percent') or 0),
            'default_page_size': request.POST.get('pos_default_page_size') or 'thermal_80',
            'default_direct_print_checked': request.POST.get('pos_default_direct_print_checked') == 'on',
            'allow_to_decrease_price': request.POST.get('pos_allow_to_decrease_price') == 'on',
            # 'allow_negative_sale': request.POST.get('pos_allow_negative_sale') == 'on',
            'require_remarks': request.POST.get('pos_require_remarks') == 'on',
            'foc_allowed': request.POST.get('pos_foc_allowed') == 'on',
        }

        purchase_config = {
            'max_row_discount_percent': float(request.POST.get('purchase_max_row_discount_percent') or 0),
            'max_total_discount_percent': float(request.POST.get('purchase_max_total_discount_percent') or 0),
            'freight_charges_allowed': request.POST.get('purchase_freight_charges_allowed') == 'on',
            'labour_charges_allowed': request.POST.get('purchase_labour_charges_allowed') == 'on',
            'unload_charges_allowed': request.POST.get('purchase_unload_charges_allowed') == 'on',
            'default_page_size': request.POST.get('purchase_default_page_size') or 'thermal_80',
            'default_direct_print_checked': request.POST.get('purchase_default_direct_print_checked') == 'on',
            'auto_update_cost_price': request.POST.get('purchase_auto_update_cost_price') == 'on',
            'foc_allowed': request.POST.get('purchase_foc_allowed') == 'on',
        }

        quotation_config = {
            'default_page_size': request.POST.get('quotation_default_page_size') or 'thermal_80',
            'default_direct_print_checked': request.POST.get('quotation_default_direct_print_checked') == 'on',
            'quotation_validity_days': int(request.POST.get('quotation_validity_days') or 30),
            'auto_convert_to_bill': request.POST.get('quotation_auto_convert_to_bill') == 'on',
        }

        voucher_config = {
            'default_page_size': request.POST.get('voucher_default_page_size') or 'thermal_80',
            'default_direct_print_checked': request.POST.get('voucher_default_direct_print_checked') == 'on',    
        }

        inventory_config = {
            'allow_negative_stock': request.POST.get('inventory_allow_negative_stock') == 'on',
            'enable_expiry_tracking': request.POST.get('inventory_enable_expiry_tracking') == 'on',
            'enable_low_stock_alerts': request.POST.get('inventory_enable_low_stock_alerts') == 'on',
        }
        
        
        stock_valuation_method = request.POST.get(
            'stock_valuation_method'
        ) or config_instance.stock_valuation_method or 'LAST_PUR_PRICE'

        allowed_methods = {
            'FIFO',
            'FEFO',
            'LIFO',
            'AVERAGE',
            'LAST_PUR_PRICE',
        }

        if stock_valuation_method not in allowed_methods:
            stock_valuation_method = 'LAST_PUR_PRICE'



        general_config = {
            'multiple_bill_prints': int(request.POST.get('general_multiple_bill_prints') or 1),
            'currency_symbol': request.POST.get('general_currency_symbol') or 'Rs',
            'company_tagline': request.POST.get('general_company_tagline') or '',
            'online_software': request.POST.get('general_online_software') == 'on',
            'stock_valuation_method': stock_valuation_method,
        }

        dashboard_default_period = request.POST.get('dashboard_default_period') or 'today'
        if dashboard_default_period not in {'today', '7_days', 'this_month'}:
            dashboard_default_period = 'today'
        dashboard_config = {
            'default_period': dashboard_default_period,
        }

        full_config_data = {
            'pos': pos_config,
            'purchase': purchase_config,
            'quotation': quotation_config,
            'vouchers': voucher_config,
            'inventory': inventory_config,
            'general': general_config,
            'dashboard': dashboard_config,
        }

        if not config_instance:
            config_instance = CompanyConfiguration(company=company, branch=branch)

        config_instance.config_data = full_config_data
        config_instance.stock_valuation_method = stock_valuation_method


        # Update legacy fields to keep consistency
        config_instance.multiple_bill_prints = general_config['multiple_bill_prints']
        config_instance.pos_sale_receipt_size = 'Thermal' if 'thermal' in pos_config['default_page_size'].lower() else pos_config['default_page_size'].upper()
        config_instance.purchase_receipt_size = 'Thermal' if 'thermal' in purchase_config['default_page_size'].lower() else purchase_config['default_page_size'].upper()
        config_instance.save()

        # Handle "Apply to All Branches"
        if request.POST.get('all_branches'):
            all_branches = Branch.objects.filter(company=company)
            for b in all_branches:
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    branch=b,
                    defaults={
                        'config_data': full_config_data,
                        'multiple_bill_prints': config_instance.multiple_bill_prints,
                        'pos_sale_receipt_size': config_instance.pos_sale_receipt_size,
                        'purchase_receipt_size': config_instance.purchase_receipt_size,
                        'stock_valuation_method': config_instance.stock_valuation_method,

                    }
                )
            messages.success(request, f"Configuration updated and applied to all branches of {company.name}.")
        else:
            messages.success(request, f"Configuration updated for {branch.name}.")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Company configuration saved successfully!'})

        if request.user.is_superuser:
            return redirect(f"{request.path}?company={company.id}&branch={branch.id}")
        return redirect('company_config')

    # On GET: load merged configurations
    merged_config, _ = get_company_config(company.id if company else None, branch.id if branch else None)
    companies = list(Company.objects.all().order_by('name')) if request.user.is_superuser else [company]
    branches = list(Branch.objects.filter(company=company).order_by('name')) if company else []
    print('merged_config',merged_config)
    context = {
        'company': company,
        'branch': branch,
        'companies': companies,
        'branches': branches,
        'config': merged_config,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'configuration/company_config.html', context)


@login_required
def get_company_config_api(request):
    """
    API endpoint returning company configuration and default accounts for the current user's company and branch.
    """
    try:
        user_profile = getattr(request.user, 'userprofile', None)
        company = getattr(user_profile, 'company', None) or Company.objects.first()
        branch = getattr(user_profile, 'branch', None) or (Branch.objects.filter(company=company).first() if company else None)

        if not company:
            company = Company.objects.first()
        if not branch:
            branch = Branch.objects.first()

        config_data, _ = get_company_config(company.id if company else None, branch.id if branch else None)
        default_accounts_data, _ = get_default_accounts(company.id if company else None, branch.id if branch else None)

        return JsonResponse({
            'success': True,
            'company': {
                'id': company.id if company else None,
                'name': company.name if company else '',
            },
            'branch': {
                'id': branch.id if branch else None,
                'name': branch.name if branch else '',
            },
            'config': config_data,
            'default_accounts': default_accounts_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f"Error loading configurations: {str(e)}"
        }, status=500)
