from django.shortcuts import render,redirect
from django.http import HttpResponse,Http404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.core.paginator import Paginator,EmptyPage,PageNotAnInteger
from datetime import datetime
from leave.models import Employee,UserProfile,Application,ApplicationLog,TransactionLog,Action,EmployeeUpdateLog
from django import forms
from leave.forms import ApplicationForm,CreditApplicationForm,SelectEmployeeForm,EmployeeEditForm,CancelForm,EmployeeNewForm
from django.contrib import messages
import json
from django.core.exceptions import PermissionDenied,ObjectDoesNotExist
from django.core import serializers
from django.db import transaction

#func to find out users department
def isDept(user):
    return user.groups.filter(name = 'depts')
def isEmployee(user):
    return user.groups.filter(name='employee')
def isAdmin(user):
    return user.groups.filter(name='admin')

def getStatus(sort):
    if sort == None:
        status = 0
    elif sort.lower() == "pending":
        status = 1
    elif sort.lower() == "processing":
        status = 2
    elif sort.lower() == "approved":
        status = 3
    elif sort.lower() == "rejected":
        status = 4
    elif sort.lower() == "cancelled":
        status = 5
    else :
        status = 0
    return status

def isCredit(type):
    if type==None:
        return False
    elif type=="Credit":
        return True
    else:
        return False

def getApplicationList(page,status,date,month,year):
    all_list=Application.objects.all().order_by('-time_generated')
    if 1<= status<=3:
        all_list=all_list.filter.all(status=status)
    if year:
        all_list=all_list.filter.all(time_generated_year=year)
    if month:
        all_list=all_list.filter.all(time_generated_month=month)
    if date:
        all_list=all_list.filter.all(time_generated_date=date)

    #Implementing Pagination
    paginator=Paginator(all_list,10)

    try:
        applications= paginator.page(page)
    except PageNotAnInteger:
        #move to first page
        applications=paginator.page(1)
    except EmptyPage:
        #if page is out of range,redirect to last page
        applications=paginator.page(paginator.num_pages)
    return applications


#Create your views here.
def index(request):
    #Authenticate user
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username = username, password = password)
        if user is not None and user.is_active():
            #Login User
            login(request,user)
        else:
            #Invalid Login
            return render(request,'leave/login.html',{'message':"Invalid Login!!",'username':username})
    
        if request.user.is_authenticated():
            if request.user.is_employee():
                redirect('admin:index')   

                userprofile=UserProfile.objects.get(user=request.user)
                #redirecting to the corresponding user page of respective user
                context={
                    'user_type':userprofile.user_type,
                }  
            else:
                context['pending_count']=Application.objects.filter(status=1).count()
                context['processing_count']=Application.objects.filter(status=2).count()            
                context['action_count']=Action.objects.filter(status=1).count()
                return render(request,'leave/admin.html',context)

        else :  
            #Redirect to login page
            return render(request,'leave/login.html',{'message':"Invalid Credentials"})

"""Func for Logout"""
def logout(request):
    logout(request)
    return redirect('login')

@login_required
@user_passes_test(isAdmin)
def manage_action(request):
    if  request.method=='POST':
        action_id=request.POST.get('action','')
        status=request.POST.get('status','')
        action_id=int(action_id)
        status=int(status)
        to_json={}
        try:
            action=Action.objects.get(pk=action_id)
        except Action.DoesNotExist:
            messages.error(request,'some error occured')
            to_json['result']=0
            to_json['message']='Some error occured'
    else:
        if status==3:
            if action.is_leave:
                entries=TransactionLog.objects.filter(action=action)
                valid=True
                for entry in entries:
                    pass
                if valid:
                    for entry in enteries:
                        entry.employee.transaction(entry.hp_change,entry.earned_change)
                        entry.hp_balance=entry.employee.hp_balance
                        entry.earned_balance=entry.employee.earned_balance
                        entry.save()
                    action.status=status
                    action.time_approved=datetime.now()
                    action.save()
                    
                    messages.success(request,'Action Approved')

                    to_json['result']=1
                    to_json['message']='Action Approved'

                else:
                    to_json['result']=0
                    to_json['message']='Cannot approve leave, Insufficient leave balance'
                    messages.error(request,'Cannot approve leave,Insufficient leave balance')
            else:
                action.status=status
                action.time_approved=datetime.now()
                action.save()
                update_log=action.update_log
                employee=update_log.employee
                employee.name=update_log.new_name
                employee.dept=update_log.new_dept
                employee.email=update_log.new_email
                employee.is_active=update_log.new_is_active
                employee.save()
                messages.success(request,'Action Approved,Employee details updated')
                to_json['result']=1
                to_json['message']='Action Approved, Employee Details Updated'
        elif status==4:
            action.status=status
            action.time_approved=datetime.now()
            action.save()
            messages.success(request,'Action Rejected')
            to_json['result']=1
            to_json['message']='Action Rejected'

        else:
            to_json['result']=0
            to_json['message']='Some error occured'
            messages.error(request,'Some error tripped in or out')
    return HttpResponse(json.dumps(to_json))

@login_required
@user_passes_test(isAdmin)
def action_history(request,sort):
    status=getStatus(sort)
    if status==0:
        messages.error(request,'Status is deleted')
    userprofile=UserProfile.objects.get(user=request.user)
    page=request.GET.get('page','')
    actions=Action.objects.all().order_by("-time_generated")
    if 1<= status <=4:
        actions=actions.filter(status=status)
        paginator=Paginator(actions,20)
        try:
            actions=paginator.page(page)
        except PageNotAnInteger:
            actions=paginator.page(1)
        except EmptyPage:
            actions=paginator.page(paginator.num_pages)
        context={
            'actions':actions,
            'user_type':userprofile.user_type,
            'status':status,
        }
    return render(request,'leave/action_history.html',context)

@login_required
def print_action(request,id):
    userprofile=UserProfile.objects.get(user=request.user)
    try:
        action=Action.objects.get(pk=id)
    except Action.DoesNotExist:
        raise Http404
    context={
        'actions':action,
        'user_type':userprofile.user_type,
    }
    if action.is_leave:
        entries=TransactionLog.objects.filter(action=action)
        page=request.GET.get('page','')
        paginator=Paginator(entries,20)
        try:
            entries=paginator.page(page)
        except PageNotAnInteger:
            entries=paginator.page(1)
        except EmptyPage:
            entries=paginator.page(paginator.num_pages)
        context['entries']=entries
    return render(request,'leave/print_action.html',context)

@login_required
def action(request,id):
    userprofile=UserProfile.objects.get(user=request.user)
    try:
        action=Action.objects.get(pk=id)
    except Action.DoesNotExist:
        raise Http404
    context={
        'actions':action,
        'user_type':userprofile.user_type,
    }
    if action.is_leave:
        entries=TransactionLog.objects.filter(action=action)
        page=request.GET.get('page','')
        paginator=Paginator(entries,20)
        try:
            entries=paginator.page(page)
        except PageNotAnInteger:
            entries=paginator.page(1)
        except EmptyPage:
            entries=paginator.page(paginator.num_pages)
        context['entries']=entries
    return render(request,'leave/action.html',context)

@login_required
@user_passes_test(isAdmin)
def actions(request,id):
    status=getStatus(sort)
    if status==0:
        status=1
    userprofile=UserProfile.objects.get(user=request.user)
    actions=Action.objects.filter(status=status)
    page=request.GET.get('page','')
    paginator=Paginator(actions,20)
    try:
        actions=paginator.page(page)
    except PageNotAnInteger:
        actions=paginator.page(1)
    except EmptyPage:
        actions=paginator.page(paginator.num_pages)
    context={
        'actions':actions,
        'user_type':userprofile.user_type,
        'status':status,
    }
    return render(request,'leave/actions.html',context)

    
#performing deleting action ,only if action is pending state
@login_required
@user_passes_test(isAdmin)
def delete_action(request):
    if request.method=='POST':
        action = Action.objects.get(pk=request.POST.get('id'))
        if action.status==1:
            action.status=0
            action.save()
            message.success(request,'Action Deleted')
        else:
            message.error(request,'Only pending action can be deleted')
            return redirect(reverse('action',args=(action.pk)))
    else:
        PermissionDenied

@login_required
@user_passes_test(isAdmin)
def manage_leave(request):
    if request.method=='pOST':
        leave_type=request.POST.get('leave_type','')
        action_type=request.POST.get('action_type')
        days=request.POST.get('count','')
        note=request.POST.get('note')
        try:
            leave_type=int(leave_type)
            action_type=int(action_type)
            days=int(days)
        except ValueError:
            messages.error(request,"Invalid Inputs")
            return redirect(reverse('employees'))
        if 1<= leave_type <=2 and days>=0 and (action_type==-1 or action_type==1):
            count=0
            employees=request.POST.getlist('check[]')
            action=Action(note=note,)
            action.save()
            
            for pk in employees:
                try:
                    employee=Employee.objects.get(pk=pk)
                except Employee.DoesNotExist:
                    pass
                else:
                    if action_type==-1 and not employee.isLeaveLeft(days,leave_type):
                        pass
                    else:
                        TransactionLog().AdminTransaction(action, employee,leave_type,days,action_type,note)
                        count=count+1
            if count:
                messages.success(request,"Leave Credit/Debit of "+str(count)+"employee sent for approval")
                action.count=count
                action.save()
            else:
                messages.error(request,"Error!,No employee selected")
                action.delete()
        else:
            messages.error(request,"Invalid Action")
            return redirect(reverse('employees'))
    else:
        raise PermissionDenied
        
@login_required
@user_passes_test(isAdmin)
def print_application(request,id):
    userprofile=UserProfile.objects.get(user=request.user)
    


@login_required
@user_passes_test(isAdmin)
def cancel(request,id):
    userprofile=UserProfile.objects.get(user=request.user)
    try:
        application=Application.objects.get(pk=id)
    except Application.DoesNotExist:
        raise Http404

    if application.employee.dept!=userprofile.dept:
        raise PermissionDenied

    if not application.is_new:
        return HttpResponse("Cancel request cannot be cancelled")
    
    if application.is_credit:
        return HttpResponse("Credit request cannot be cancelled")
    
    if application.status!=3:
        return HttpResponse("This application is now"+application.get_status_display()+",Cancelation request can only be initiated for APPROVED Applications")

    if application.original:
        messages.error(request,"There already exist cancel request for this application")
        return redirect(reverse('details',args=(application.original.pk,)))
    
    new_form=CancelForm()
    context={
        'user_type':userprofile.user_type,
        'form':new_form,
        'application':application,
    }
    if request.method=='POST' :
        form=CancelForm(request.POST,request.FILES)
        if form.is_valid():
            reason=form.cleaned_data['reason']
            cancel_application=application.CancelRequest(reason)
            activity="Application generated by" + userprofile.get_user_type_display()

@login_required
@user_passes_test(isDept)
def delete_application(request) :
    if request.method == 'POST' :
        userprofile = UserProfile.objects.get(user=request.get)
        application_id = request.POST.get('id')
        application = Application.objects.get(pk=application_id)
        if application.employee.dept == userprofile.dept and application.status == 1:
            application.status = 0

            if not application.is_new:
                application.original = None
                application.original.save()

            application.save()

            activity = "Application Deleted by" + userprofile.get_user_type_display()
            log_entry = ApplicationLog(application=application,time=datetime.now,activity=activity)
            log_entry.save()
            messages.success(request,"Application Deleted")

        else:
            messages.error("Some error occured,Cannot delete application")
        return redirect(reverse(details,args = (application.pk,)))  
    else:
        raise PermissionDenied



@login_required
@user_passes_test(isAdmin)
def start_processing(request):
    if request.method=='POST':
        userprofile=UserProfile.objects.get(user=request.user)
        user_type=userprofile.user_type
        application_id=request.POST.get('id')
        application=Application.objects.get(pk=application_id)
        to_json={}
        notes=request.POST.get('notes',"")

        if application.status==1 and isAdmin(request.user):
            application.status=2
            application.save()
            activity="Processing Started"
            log_entry=ApplicationLog(application=application,time=datetime.now(),activity=activity,notes=notes)
            log_entry.save()
            to_json['result']=1
            to_json['message']='Application marked as Processing'
            messages.success(request,'Application marked as Processing')
        else:
            to_json['result']=0
            to_json['message']='Error'
            messages.error(request,'Cannot change status,Try again')
        return HttpResponse(json.dumps(to_json))
    else:
        PermissionDenied

@login_required
@user_passes_test(isAdmin)
def employees(request):
    userprofile=UserProfile.objects.get(user=request.user)
    employees=Employee.objects.filter(is_active=True)
    serializer=EmployeeSerializer()
    serialized_employee=serializer.serialize(employees)

    context={
        'employees':serialized_employee,
        'user_type':userprofile.user_type,
    }
    return render(request,'leave/employees..html',context)

@login_required
@user_passes_test(isAdmin)
def select_employee(request):
    userprofile=UserProfile.objects.get(user=request.user)
    dept=None
    if isDept(request.user):
        dept=userprofile.dept

    user_type=userprofile.user_type

    form=SelectEmployeeForm(dept,user_type)
    if request.method=='POST':
        form=SelectEmployeeForm(dept,user_type,request.POST)
        if form.is_valid():
            employee=form.cleaned_data['employee']
            return redirect(reverse('employee',args=(employee.pk,)))

    context={
        'form':form,
        'user_type':user_type,
    }
    return render(request,'leave/select_employee.html',context)

@login_required
@user_passes_test(isAdmin)
def edit_employee(request,id):
    userprofile=UserProfile.objects.get(user=request.user)
    try:
        employee=Employee.objects.get(pk=id)
    except Employee.DoesNotExist:
        return Http404
    try:
        action=Action.objects.get(is_leave=False,status=1,update_log_employee=employee)
        messages.success(request,'An update action is already pending')
        return redirect(reverse('action',args=(action.pk,)))
    except Action.DoesNotExist:
        pass

    form=EmployeeEditForm(initial={'new_name':employee.name,'new_email':employee.email,
    'new_dept':employee.dept,'new_is_active':employee.is_active})
    context={
        'employee':employee,
        'form':form,
        'user_type':userprofile.user_type,
    }
    if request.method=='POST':
        form=EmployeeEditForm(request.POST)
        if form.is_valid():        
            new_name=form.cleaned_data['new_name']
            new_email=form.cleaned_data['new_email']
            new_dept=form.cleaned_data['new_dept']
            new_is_active=form.cleaned_data['new_is_active']
            note=form.cleaned_data['note']
            if (new_name==employee.name and new_dept==employee.dept and new_email==employee.email 
            and new_is_active==employee.is_active):
                messages.error("No details updated")
                context['form']=form
            else:
                action=Action(note=note,is_leave=False)
                action.save()
                update=EmployeeUpdateLog(action=action,employee=employee,new_name=new_name,
                new_dept=new_dept,new_email=new_email,new_is_active=new_is_active,old_name=employee.name
                ,old_dept=employee.dept,old_email=employee.email,old_is_active=employee.is_active)
                update.save()
                messages.success(request,'Employee details update sent')
                return redirect(reverse('action',args=(action.pk,)))
        else:
            messages.error("Please do correct ,Incorrect fields")
            context['form']=form
        return redirect(request,'leave/edit_employee.html',context)
    else:
        return redirect(request,'leave/edit_employee.html',context)

@login_required
@user_passes_test(isAdmin)
def new_employee(request):
    userprofile=UserProfile.objects.get(user=request.user)
    context={
        'user_type':UserProfile.user_type,
    }
    if request.method=='POST':
        form=EmployeeNewForm(request.POST)
        qci_id=form.data['qci_id']
        try:
            employee=Employee.objects.filter(is_active=False).get(qci_id=qci_id)
            messages.success(request,'Employee Id already exits,upload details here')
            return redirect(reverse('edit_employee',args=(employee.pk,)))
        except Employee.DoesNotExist:
            if form.is_valid():
                new_employee=form.save()
                note="Adding new Employee"
                action=Action(note=note,is_leave=False)
                action.save()
                update=EmployeeUpdateLog(action=action,is_new=True,employee=new_employee,new_name=new_employee.name,new_dept=new_employee.dept,new_email=new_employee.email,new_is_active=True)
                update.save()
                messages.success(request,'New Employee is going to be added')
                return redirect(reverse('action',args=(action.pk,)))
            else:
                messages.error(request,'Please correct,Incorrect fields')
                context['form']=form
        return redirect(request,'leave/new_employee.html',context)
    else:
        context['form']=EmployeeNewForm()
        return render(request,'leave/new_employee.html',context)    

@login_required
@user_passes_test(isDept)
def sent(request,sort,year,month,date):
    userprofile=UserProfile.objects.get(user=request.user)
    status=getStatus(sort)
    page=request.GET.get('page')
    applications=getApplicationList(page,status,year,monthdate)
    context={
        'name':request.user.username,
        'dept':userprofile.dept.name,
        'applications':applications,
        'status':status,
        'user_type':userprofile.user_type,
    }
    return render(request,'leave/sent.html',context)

@login_required
@user_passes_test(isDept)
def dept(request):
    userprofile=UserProfile.objects.get(user=request.user)
    context={
        'user_type':userprofile.user_type
    }
    return render(request,'leave/dept.html',context)

@login_required
@user_passes_test(isDept)
def new_application(request,type):
    #information particular to each user
    userprofile=UserProfile.objects.get(user=request.user)
    context={
        'name':request.user.username,
        'dept':userprofile.dept.name,
        'user_type':userprofile.user_type,
        'is_credit':isCredit(type)
    }
    if request.method=='POST':
        if isCredit(type):
            form=CreditApplicationForm(userprofile.dept,request.POST,request.FILES)
        else:
            form=ApplicationForm(userprofile.dept,request.POST,request.FILES)
        
        if form.is_valid():
            new_application=form.save()
            if not isCredit(type):
                new_application.new_date_from=new_application.date_from
                new_application.new_date_to=new_application.date_to
                new_application.save()

            activity="Application generated by"+userprofile.get_user_type_display()
            log_entry=ApplicationLog(Application=Application,time=datetime.now,activity=activity)
            log_entry.save()
            messages.success(request,'Application')
            return redirect(reverse(details,args=(new_application.pk,)))

        else:
            context['form']=form

    else:
        if isCredit(type):
            form=CreditApplicationForm(userprofile.dept)
        else:
            form=ApplicationForm(userprofile.dept)
        context['form']=form
        return render(request,'leave/new_application.html',context)

@login_required
def applications(request,sort,year,month,date):
    if isAdmin(request.user):
        return admin(request,sort,year,month,date)
    else:
        return Http404

@login_required
@user_passes_test(isAdmin)
def admin(request,sort,year,month,date):
    page=request.GET.get('page')
    userprofile=UserProfile.objects.get(user=request.user)
    status=getStatus(sort)
    if not sort or status==0:
        sort=''
    if status==0:
        status=3
    url=reverse('applications',args=(sort,))
    if not sort=='':
        url=url+'/'

    applications=getApplicationList(page,status,year,month,date)
    context={
        'name':request.user.username,
        'application':applications,
        'status':status,
        'user_type':userprofile.user_type,
        'current_url':url
    }
    return render(request,'leave/admin.html',context)

@login_required
def user_guide(request):
    userprofile=UserProfile.objects.get(user=request.user)
    context={
        'user_type':userprofile.user_type
    }
    return render(request,'leave/user_guide.html',context)

