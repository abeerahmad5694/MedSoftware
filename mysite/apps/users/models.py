from django.db import models
from apps.configuration.models import Company, Branch
# Create your models here.


from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey('configuration.Company', on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    terminal = models.ForeignKey('configuration.POSTerminal', on_delete=models.SET_NULL, null=True, blank=True)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_permissions(self):
        return self.role.permissions.all()
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE)
    permissions = models.ManyToManyField('Permission', blank=True)
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('name', 'company')


class Permission(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50)  # sales, inventory, etc.
    dateent = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name



# Permission.objects.create(
#     name="Edit Invoice",
#     code="edit_invoice",
#     module="sales"
# )


# user_permissions = request.user.userprofile.role.permissions.all()

# if user_permissions.filter(code="create_invoice").exists():
#     # allow action