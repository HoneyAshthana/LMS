from django import forms
from leave.models import Department,Employee,Application
from datetime import datetime
from django.forms.widgets import SelectDateWidget
from django.forms import Textarea,ModelForm,DateInput,save_instance
"""Application form"""
class ApplicationForm(ModelForm):
    class Meta:
        model=Application
        fields=['employee','leave_type','date_from','date_to','reason']
        widgets={'reason',Textarea(attrs={'cols':10,'rows':5})}
    
    def is_valid(self):
        valid = super(ApplicationForm,self).is_valid()
        if not valid:
            return valid
        
        employee = self.cleaned_data['employee']
        leave_type = self.cleaned_data['leave_type']
        date_from = self.cleaned_data['date_from']
        date_to = self.cleaned_data['date_to']

        if date_from > date_to:
            self.errors['date_to']=['Invalid To Date']
            return False

        if not employee.isLeaveLeft((date_to-date_from).days+1,leave_type):
            self.errors['date_to']=["Insufficient Leave Balance"]
            return False

        return True

"""Credit application form"""
class CreditApplicationForm(ModelForm):
    class Meta:
        model=Application
        fields=['employee','leave_type','is_credit','days','reason']
        widgets={'reason':Textarea(attrs={'cols':10,'rows':5}),'is_credit':forms.HiddenInput()}

    def is_valid(self):
        valid=super(CreditApplicationForm,self).is_valid()
        if not valid:
            return valid

        employee = self.cleaned_data['employee']
        days = self.cleaned_data['days']
        leave_type=self.cleaned_data['leave_type']

        if days<=0:
            self.errors['days']=['Please enter positive correct Date']
            return False
        
        return True

""""Cancelation Form"""
"""
class CancelForm(ModelForm):
    def __init__(self,*args):
        super(CancelForm,self).__init__(*args)
        reason=forms.CharField(widget=forms.Textarea)"""

"""Form when admin want to view particular employee form"""
class SelectEmployeeForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.all(),label='')

    def __init__(self,dept,user_type,*args,**kwargs):
        super(SelectEmployeeForm,self).__init__(*args,**kwargs)

        employees=Employee.objects.all()
        if user_type!=5:
            self.fields['employee'].queryset=Employee.objects.filter(is_active=True)
        if dept:
            self.fields['employee'].queryset=Employee.objects.filter(dept=dept,is_active=True)

"""Employee Edit Form"""
class EmployeeEditForm(ModelForm):
    new_name=forms.CharField(max_length=50)
    new_dept=forms.CharField(max_length=20)
    new_emaid=forms.EmailField(max_length=50)
    
    def __init__(self,*args,**kwargs):
        super(EmployeeEditForm,self).__init__(self,*args,**kwargs)
        self.fields['new_name'].label="New Name"
        self.fields['new_dept'].label="New Department"
        self.fields['new_email'].label="New Email"
        self.fields['note'].label="Note"

"""New Employee Form"""
class EmployeeNewForm(ModelForm):
    def __init__(self,*args,**kwargs):
        super(EmployeeNewForm,self).__init__(*args,**kwargs)

    def save(self,commit=True):
        if self.instance.pk is None:
            fail_message='created'
        else:
            fail_message='changed'

        return save_instance(self,self.instance,fail_message,commit,construct=False,)

    class Meta:
        model=Employee
        fields=['qci_id','name','dept','email']
