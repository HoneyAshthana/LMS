from django.db import models
from datetime import datetime
from django.contrib.auth.models import User

#different types of users
USER_TYPES=(
    (1,'admin'),
    (2,'employees')
)

#kind of leave of employees
LEAVE_TYPES = (
    (1,'Earned Leave'),
    (2,'Half pay leave'),
    (3,'Commuted leave')
)

#status of application
STATUS=(
    (0,'Deleted'),
    (1,'Pending'),
    (2,'Approved'),
    (3,'Rejected')
)

# Create your models here.
class Department(models.Model):
    name=models.CharField(max_length=100)
    def __unicode__(self):
        return self.name

#Model for employees
class Employee(models.Model):
    qci_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    dept = models.ForeignKey('Department',on_delete=models.CASCADE)
    #for normal leave
    earned_balance = models.IntegerField(default=0) 
    #half-pay leave
    hp_balance = models.IntegerField(default=0)     
    email = models.EmailField(max_length=100)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        return self.qci_id + ":" + self.name

    def isLeaveLeft(self,leave_type,days):
        """func returns true only if leave can be granted """
        if  leave_type == 1 :
            return days<=self.earned_balance
        elif leave_type == 2 :
            return days<=self.hp_balance
        elif leave_type == 3 :
            return days*2<=self.hp_balance   
        else :
            return False

    def approveTransaction(self,leave_type,days,action_type):
        earned_change=0
        hp_change=0
        if leave_type == 1:
            earned_change+=days*action_type
        elif leave_type == 2:
            hp_change+=days*action_type
        elif leave_type == 3:
            hp_change+=2*days*action_type
        self.transaction(hp_change,earned_change)
        return True

    def transaction(self,hp_change,earned_change):
        self.earned_balance -= earned_change
        self.hp_balance -= hp_change
        self.save()
        return True

class EmployeeUpdateLog(models.Model):
    action=models.OneToOneField('Action',related_name='update_log',on_delete=models.CASCADE)
    employee = models.ForeignKey('Employee',on_delete=models.CASCADE)
    is_new = models.BooleanField(default = False)
    new_name = models.CharField(max_length = 100)
    new_email = models.EmailField(max_length =75)
    new_dept = models.ForeignKey('Department',related_name = 'update_new_dept',on_delete=models.CASCADE)
    new_is_active = models.BooleanField(default = False)
    old_name = models.CharField(max_length = 100)
    old_dept = models.ForeignKey('Department',related_name = 'update_old_dept',on_delete=models.CASCADE)
    old_email = models.EmailField(max_length = 75)
    old_is_active=models.BooleanField(default = True)

#Model to represent different types of users
class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    user_type = models.IntegerField(choices=USER_TYPES)
    dept = models.ForeignKey('Department',on_delete=models.CASCADE)

class Action(models.Model):
    count = models.IntegerField(default = 0)
    is_leave = models.BooleanField(default =False)
    note = models.TextField(max_length=100,blank=False,null=True)
    status = models.IntegerField(choices=STATUS,default=1)
    time_generated = models.DateTimeField(auto_now_add = True)
    time_approved = models.DateTimeField(null=True)
    reply_note = models.TextField(blank =False,null = True)
    
    def to_text(self):
        if self.is_leave :
            return "Leave Credit/Debit"
        else:
            if self.update_log.is_new:
                return "Add new Employee"
            else:
                return "Edit Employee Detail"

class ApplicationLog(models.Model):
    application = models.ForeignKey('Application',on_delete=models.CASCADE)
    time = models.DateTimeField()
    activity = models.TextField(max_length=100,null=True,blank =True)
    notes = models.TextField(max_length=100,blank=True,null=True)

class TransactionLog(models.Model):
    employee = models.ForeignKey('Employee',on_delete=models.CASCADE)
    action = models.ForeignKey('Action',null=True,on_delete=models.CASCADE)
    application = models.ForeignKey('Application',null=True,on_delete=models.CASCADE)
    is_admin = models.BooleanField(default = False)
    earned_balance = models.IntegerField()
    earned_change = models.IntegerField(default=0)
    hp_balance = models.IntegerField()
    hp_change = models.IntegerField(default = 0)
    note = models.TextField(max_length=100,null=True,blank=True)
    time = models.DateTimeField(null=True)

    def to_text(self):
        change=0
        text=""

        if self.hp_change:
            change=self.hp_change
            text+=str(abs(change))+"HalfPay Leave"
        elif self.earned_change:
            change=self.earned_change
            text+=str(abs(change))+"Earned Leave"

        if change<0:
            text+="Debit"
        elif change>0:
            text+="Credit"
        else:
            return "No changes in leave balance"
        return text
    
    def applicationTransaction(self,employee,application):
        earned_balance = employee.earned_balance
        hp_balance = employee.hp_balance
        earned_change = 0
        hp_change = 0
        """Add application"""
        if application.is_credit:
            if application.is_new:
                action_type = 1
            else:
                action_type = -1
        else:
            pass
            """
            #delete application
            if application.is_new:
                action_type = -1
            else:
                action_type = 1"""
        if application.is_credit:
            days = application.days
        else:
            days = (application.new_date_to-application.new_date_from).days+1

        if application.leave_type == 1:
            earned_change+=days*action_type
        elif application.leave_type == 2:
            hp_change+=days*action_type
        elif application.leave_type == 3:
            hp_change+=2*days*action_type
        self.employee = employee
        self.application = application
        self.earned_balance = earned_balance
        self.earned_change = earned_change
        self.hp_balance = hp_balance   
        self.hp_change = hp_change
        self.time = datetime.now()
        self.save() 

    def adminTransaction(self,employee,leave_type,days,note,action,action_type):
        earned_balance=employee.earned_balance
        hp_balance=employee.hp_balance
        earned_change=0
        hp_change=0
        if leave_type == 1:
            earned_change+=days*action_type
        if leave_type == 2:
            hp_change+=days*action_type

        if leave_type == 3:
            hp_change+=2*days*action_type

        self.action=action
        print (action)
        self.employee=employee
        self.leave_type=leave_type
        self.is_admin=True
        self.earned_balance=earned_balance
        self.earned_change=earned_change
        self.hp_balance=hp_balance
        self.hp_change=hp_change
        self.time=datetime.now()
        self.note=note
        self.save()
        
#model to represent individual application
class Application(models.Model):
    employee = models.ForeignKey('Employee',on_delete=models.CASCADE)
    is_new = models.BooleanField(default=True)
    is_credit = models.BooleanField(default=False)
    #original field of new applicationsrefers to ongoing cancel request for the same
    original = models.ForeignKey('self',null=True,on_delete=models.CASCADE)
    leave_type = models.IntegerField(choices=LEAVE_TYPES)
    date_from = models.DateField(null=True)
    date_to = models.DateField(null = True)
    days = models.IntegerField(default=0)
    status = models.IntegerField(choices=STATUS,default=1)
    reason = models.TextField(max_length=200)
    new_date_from = models.DateField(null=True)
    new_date_to = models.DateField(null=True)
    #fields only set when the leave is approved
    time_generated = models.DateTimeField(auto_now_add=True)
    time_received = models.DateTimeField(null=True)
    time_approved = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.employee.name + "-" + get_leave_type_display()

    def to_text(self):
        text=""
        if self.is_new and not self.is_credit:
            text+="New"+self.get_leave_type_display()+""
        elif self.is_new and self.is_credit:
            text+="Credit"+self.get_leave_type_display()+""
        else:
            text="Cancel Approved Leave"
        return text
"""
    def cancelRequest(self,reason):
        cancel_application=Application(original=self,is_new=False,employee=self.employee,leave_type=
        self.leave_type,date_from=self.date_from,date_to=self.date_to,new_date_from=self.new_date_from,
        new_date_to=self.new_date_to,reason=self.reason)
        cancel_application.save()
        self.original=cancel_application
        self.save()
        return cancel_application"""