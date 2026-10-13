from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.configuration.forms.branch import BranchForm
from apps.configuration.models import Company, Branch
from django.contrib import messages

@login_required

def branch(request):
    can_view, message = get_user_perms(request, 'configure_system')
    if not can_view:
        return redirect('page_not_found')

    company = Company.objects.first()
    branches = Branch.objects.filter(company=company).order_by('-id')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        branch_id = request.POST.get('branch_id')

        # === DELETE BRANCH ===
        if action == 'delete':
            if not request.user.is_superuser:
                messages.error(request, 'Not authorized to delete')
                return redirect('branch')

            # if branch_id == 1:
            #     messages.error(request, 'Not authorized to delete main branch')
            total_branches = Branch.objects.filter(company=company).count()
            if total_branches <= 1:
                messages.error(request, 'Cannot delete the last branch. At least one branch must remain.')
                return redirect('branch')
                # return redirect('branch')
            # print('brach_id',branch_id)

            del_obj = Branch.objects.filter(id=branch_id, company=company).first()
            if del_obj:
                if del_obj.logo:
                    del_obj.logo.delete(save=False)
                del_obj.delete()
                messages.success(request, f'Branch "{del_obj.name}" deleted successfully')
            else:
                messages.error(request, 'Branch not found')
            return redirect('branch')

        # === CREATE / UPDATE ===
        if branch_id:
            instance = Branch.objects.filter(id=branch_id).first()
            form = BranchForm(request.POST, request.FILES, instance=instance)
        else:
            form = BranchForm(request.POST, request.FILES)

        if not request.user.is_superuser:
            messages.error(request, 'You are not authorized')
            return redirect('branch')

        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.company:
                obj.company = company

            # If delete_logo checked
            if request.POST.get('delete_logo') == '1':
                if obj.logo:
                    # delete file from storage but keep obj
                    if instance and instance.logo:
                        instance.logo.delete(save=False)
                    obj.logo = None
                # Also if instance exists and user clicked delete without new file
                # we already cleared it

            obj.save()
            msg = 'Updated' if branch_id else 'Created'
            messages.success(request, f'Branch {msg} successfully')
            return redirect('branch')
        else:
            messages.error(request, f'Error: {form.errors}')
            # return with form to show errors
            return render(request, 'configuration/branch.html', {
                'form': form,
                'branches': branches
            })

    # GET
    form = BranchForm()
    return render(request, 'configuration/branch.html', {
        'form': form,
        'branches': branches
    })