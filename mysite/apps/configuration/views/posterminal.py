from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.configuration.models import POSTerminal
from apps.configuration.forms.posterminal import POSTerminalForm

@login_required

def posterminal(request):
    can_view, message = get_user_perms(request, 'configure_system')
    if not can_view:
        return redirect('page_not_found')

    terminals = POSTerminal.objects.all().order_by('-id')
    
    if request.method == 'POST':
        # Handle Delete
        if 'delete_id' in request.POST:
            if not request.user.is_superuser:
                messages.error(request, 'You are not authorized to delete terminals.')
                return redirect('posterminal')
            
            terminal_id = request.POST.get('delete_id')
            terminal = get_object_or_404(POSTerminal, id=terminal_id)
            terminal.delete()
            messages.success(request, 'Terminal deleted successfully.')
            return redirect('posterminal')

        # Handle Create/Update
        terminal_id = request.POST.get('terminal_id')
        if terminal_id:
            instance = get_object_or_404(POSTerminal, id=terminal_id)
            form = POSTerminalForm(request.POST, instance=instance)
        else:
            form = POSTerminalForm(request.POST)

        if request.user.is_superuser:
            if form.is_valid():
                form.save()
                messages.success(request, 'Terminal saved successfully.')
                return redirect('posterminal')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            messages.error(request, 'You are not authorized to perform this action.')
            return redirect('posterminal')

    else:
        form = POSTerminalForm()

    return render(request, 'configuration/posterminal.html', {
        'form': form,
        'terminals': terminals
    })
