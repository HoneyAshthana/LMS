from django.contrib import admin
from leave.models import Department,Employee,EmployeeUpdateLog,UserProfile,Action,ApplicationLog,TransactionLog,Application
# Register your models here.
admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(EmployeeUpdateLog)
admin.site.register(UserProfile)
admin.site.register(Action)
admin.site.register(ApplicationLog)
admin.site.register(TransactionLog)
admin.site.register(Application)