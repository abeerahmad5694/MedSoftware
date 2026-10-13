def get_fixed_filters(request):
    fixed_filter = {}
    userprofile = getattr(request.user,'userprofile',None)
    if userprofile:
        company = userprofile.company
        branch = userprofile.branch
        terminal = userprofile.terminal
        fixed_filter['USER'] = request.user.username
        fixed_filter['COMPANY'] = company
        fixed_filter['BRANCH'] = branch
        fixed_filter['POSTERMINAL'] = terminal
    return fixed_filter 
        