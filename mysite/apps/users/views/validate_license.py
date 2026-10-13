from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from apps.users.api.license import save_license
from apps.configuration.models import Company
def validate_license_api(request):
    if request.method!= "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})

    try:
        body = json.loads(request.body)
        # company_name = body.get('company_name', '').strip()
        license_key = body.get('license_key', '').strip().upper()
        company_name = Company.objects.filter().first().name
        if not company_name or not license_key:
            return JsonResponse({"success": False, "message": "Company name and license key are required."})

        success, message = save_license(license_key, company_name)

        # message is already user-friendly from production file
        return JsonResponse({"success": success, "message": message})

    except Exception as e:
        print(f"License API error: {e}")
        return JsonResponse({"success": False, "message": "Server error. Please contact support."})