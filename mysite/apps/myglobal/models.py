from django.db import models
from django.utils import timezone


class LocalDbSyncHistory(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )


    model_name = models.CharField(max_length=150, db_index=True)

    last_update_time = models.DateTimeField(null=True, blank=True)    
    
    records_synced = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    company = models.ForeignKey('configuration.Company', on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey('configuration.Branch', on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "branch","model_name"]),
        ]

    def __str__(self):
        return f"{self.company} - {self.branch} - {self.model_name} - {self.status}"