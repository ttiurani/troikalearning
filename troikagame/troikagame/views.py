'''
Created on 14.8.2012

@author: ttiurani
'''
from troikagame import app
from security import validate_login, register, hash_password, get_troika_access_right, activatable
from backend import *
from forms import *
from flask import request, session, flash, redirect, url_for, render_template
import time

@app.route('/front')
def front():
    return redirect(url_for('troikas'))

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@app.route('/')
def troikas():
    active_troikas = get_active_troikas()
    active_entries = [dict(id=active_troika.id,
                        start_time=active_troika.start_time, 
                        title=active_troika.title, 
                        description=active_troika.description) 
               for active_troika in active_troikas]
    pending_troikas = get_pending_troikas()
    pending_entries = [dict(id=pending_troika.id,
                        start_time=pending_troika.start_time, 
                        title=pending_troika.title, 
                        description=pending_troika.description) 
               for pending_troika in pending_troikas]
    completed_troikas = get_completed_troikas()
    completed_entries = [dict(id=completed_troika.id,
                        start_time=completed_troika.start_time, 
                        title=completed_troika.title, 
                        description=completed_troika.description) 
               for completed_troika in completed_troikas]
    return render_template('troikas.html', 
                           active_entries=active_entries,
                           pending_entries=pending_entries,
                           completed_entries=completed_entries)

@app.route('/login', methods=['GET', 'POST'])
def login():
    loginerrors = []
    regerrors = []
    regform = RegistrationForm(prefix="register")
    loginform = LoginForm(prefix="login")
    if loginform.email.data and loginform.validate_on_submit():
        if (validate_login(loginform.email.data, loginform.password.data)):
            session['logged_in'] = True
            session['email'] = loginform.email.data
            flash('You were logged in')
            destination = url_for('troikas')
            if 'destination' in session:
                destination = session['destination']
                session.pop('destination', None)
            return redirect(destination)
        else:
            loginerrors.append('Invalid email/password')
    if loginform.errors:
        for key, value in loginform.errors.items():
            loginerrors.append(key + ': ' + value[0])
    if regform.email.data and regform.validate_on_submit():
        register(regform.first_name.data, regform.last_name.data,
                 regform.handle.data, regform.email.data, 
                 regform.password.data);
        session['logged_in'] = True
        session['email'] = regform.email.data
        flash('Registration successful, you were logged in')
        destination = url_for('troikas')
        if 'destination' in session:
            destination = session['destination']
            session.pop('destination', None)
        return redirect(destination)
    if regform.errors:
        for key, value in regform.errors.items():
            regerrors.append(key + ': ' + value[0])

    return render_template('login.html', loginform=loginform, regform=regform, 
                           loginerrors=loginerrors, regerrors=regerrors)

def __check_login(destination = None, url = None):
    if not 'logged_in' in session:
        if url is None:
            url = url_for(destination)
        flash('You need to login first')
        session['destination'] = url
        return redirect(url_for('login'))

@app.route('/user', methods=['GET', 'POST'])
def user():
    __check_login('user')
    usererrors = []
    userform = UserForm(prefix="user")
    user = get_user(session['email'])
    if request.method == 'GET':
        # Add default values
        userform.email.data = user.email
        userform.first_name.data = user.short_name
        userform.last_name.data = user.family_name
        userform.handle.data = user.handle
    elif userform.validate_on_submit(): 
        if (validate_login(session['email'], userform.password.data)):
            # Update info
            user.email = userform.email.data
            user.short_name = userform.first_name.data 
            user.family_name = userform.last_name.data
            user.full_name = userform.first_name.data + " " + userform.last_name.data
            user.handle = userform.handle.data
            if (userform.new_password.data):
                user.password = hash_password(userform.new_password.data)
            save_user(user)
            flash('Information updated')
        else:
            usererrors.append('Invalid password')
    if userform.errors:
        for key, value in userform.errors.items():
            usererrors.append(key + ': ' + value[0])

    return render_template('user.html', userform=userform, usererrors=usererrors)

def __participating(user, troika):
    if user == None:
        return False
    if user == troika.teacher:
        return 'teacher'
    if user == troika.first_learner:
        return 'first_learner'
    if user == troika.second_learner:
        return 'second_learner'
    if troika.get_phase() != 'complete' and user in troika.participants:
        return 'participant'
    return False

@app.route('/troika/<troika_id>')
def troika(troika_id):
    troika = get_troika(troika_id);
    access=False
    activate=False
    user = None
    if 'logged_in' in session:
        user = get_user(session['email'])
        access = get_troika_access_right(user, troika)
        activate = activatable(user, troika, app.config.get('ACTIVATABLE_BEFORE_THREE'))
    
    entry = {'access': access,
             'activate': activate,
             'id': troika.id,
             'phase': troika.get_phase(),
             'title': troika.title, 
             'description': troika.description,
             'address': troika.address,
             'address_addendum': troika.address_addendum,
             'start_time': __get_formatted_datetime(troika.start_time,"%d.%m.%Y %H:%M"),
             'end_time': __get_formatted_datetime(troika.end_time,"%d.%m.%Y %H:%M"),
             'max_participants': troika.max_participants,
             'participating': __participating(user, troika),
             'teacher': troika.teacher.full_name if troika.teacher != None else None,
             'first_learner': troika.first_learner.full_name if troika.first_learner != None else None,
             'second_learner': troika.second_learner.full_name if troika.second_learner != None else None,
             'participants': [dict(id=participant.id,
                                full_name=participant.full_name) 
                                for participant in troika.participants] if troika.participants != None else None
             }

    # show the troika with the given id
    return render_template('troika.html', 
                           troika=entry)

def __get_start_datetime(start_date, start_time_hours, start_time_minutes):
    if start_date is None or start_time_hours is None:
        return None
    start_datetime = datetime.datetime.combine(start_date, datetime.time())
    start_datetime = start_datetime.replace(hour=start_time_hours, minute=start_time_minutes, second=0, microsecond=0)
    return start_datetime

def __get_end_datetime(start_datetime, duration):
    if start_datetime is None or duration is None:
        return None
    return start_datetime + datetime.timedelta(minutes=duration)

def __get_duration(start_datetime, end_datetime):
    if start_datetime is None or end_datetime is None:
        return None
    duration = end_datetime - start_datetime
    return duration.seconds//60 

def __get_formatted_datetime(dt, dt_format):
    if dt is None or dt_format is None:
        return None
    return dt.strftime(dt_format)

@app.route('/troika/<troika_id>/edit', methods=['GET', 'POST'])
def edit_troika(troika_id):
    __check_login(url = url_for('edit_troika', troika_id = troika_id))
    troikaerrors = []
    troikaform = TroikaForm(prefix="troika")
    # Find out if the logged in user has rights to edit/delete
    troika = get_troika(troika_id);
    user = get_user(session['email'])
    access = get_troika_access_right(user, troika)
    if not access:
        flash('Only the creator or the teacher can edit the Troika', 'error')
        return redirect(url_for('troika', troika_id=troika_id))

    if request.method == 'GET':
        # Add default values
        troikaform.title.data = troika.title
        troikaform.description.data = troika.description
        troikaform.address.data = troika.address
        troikaform.address_addendum.data = troika.address_addendum        
        troikaform.start_date.data = troika.start_time
        troikaform.start_time_hours.data = __get_formatted_datetime(troika.start_time,"%H")
        troikaform.start_time_minutes.data = __get_formatted_datetime(troika.start_time,"%M")
        troikaform.duration.data = __get_duration(troika.start_time, troika.end_time)
        troikaform.max_participants.data = troika.max_participants
    elif troikaform.validate_on_submit(): 
        if request.form["action"] == "Save Troika":
            # Update info
            troika.title = troikaform.title.data
            troika.description = troikaform.description.data 
            troika.address = troikaform.address.data
            troika.address_addendum = troikaform.address_addendum.data
            troika.start_time = __get_start_datetime(troikaform.start_date.data, troikaform.start_time_hours.data, troikaform.start_time_minutes.data) 
            troika.end_time = __get_end_datetime(troika.start_time, troikaform.duration.data)
            troika.max_participants = troikaform.max_participants.data
            save_troika(troika)
            return redirect(url_for('troika', troika_id=troika_id))
            flash('Troika saved')         
        elif request.form["action"] == "Delete Troika":
            title = troika.title
            delete_troika(troika)
            flash('Troika "' + title +  '" deleted')
            return redirect(url_for('troikas'))
    if troikaform.errors:
        for key, value in troikaform.errors.items():
            troikaerrors.append(key + ': ' + value[0])

    return render_template('edit_troika.html', 
                           troikaform=troikaform, troikaerrors=troikaerrors,
                           access=access)

@app.route('/troika/<troika_id>/activate', methods=['GET'])
def activate_troika(troika_id):
    __check_login(url = url_for('activate_troika', troika_id = troika_id))
    troika = get_troika(troika_id);
    user = get_user(session['email'])
    if activatable(user, troika, app.config.get('ACTIVATABLE_BEFORE_THREE')):
        troika.activated = datetime.datetime.now()
        save_troika(troika)
        flash('Troika "' + troika.title +  '" activated')
        return redirect(url_for('troika', troika_id=troika_id))
    else:
        flash('Troika can only be activated by the teacher after all required information is set', 'error')
        return redirect(url_for('troika', troika_id=troika_id))

@app.route('/troika/<troika_id>/<troika_role>/join', methods=['GET'])
def join_troika(troika_id, troika_role):
    __check_login(url = url_for('join_troika', troika_id = troika_id, troika_role = troika_role))
    troika = get_troika(troika_id);
    user = get_user(session['email'])
    
    if not __participating(user, troika):
        if troika_role == '0':
            if troika.teacher is not None:
                flash('The Troika already has a teacher', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.teacher = user
            save_troika(troika)
            flash('You are now teaching "' + troika.title +  '"!')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '1':
            if troika.first_learner is not None:
                flash('The Troika already has a first learner', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.first_learner = user
            save_troika(troika)
            flash('You are now the first learner of "' + troika.title +  '"!')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '2':
            if troika.second_learner is not None:
                flash('The Troika already has a second learner', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.second_learner = user
            save_troika(troika)
            flash('You are now the second learner of "' + troika.title +  '"!')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '3':
            if user in troika.participants:
                flash('You are already participating in the Troika', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.participants.append(user)
            save_troika(troika)
            flash('You are now participating in "' + troika.title +  '"!')
            return redirect(url_for('troika', troika_id=troika_id))
        else:
            flash('Unknown Troika role: ' + troika_role, 'error')
            return redirect(url_for('troika', troika_id=troika_id))
    else:
        flash('You are already partipating in the Troika.', 'error')
        return redirect(url_for('troika', troika_id=troika_id))
        
    
@app.route('/troika/<troika_id>/<troika_role>/leave', methods=['GET'])
def leave_troika(troika_id, troika_role):
    __check_login(url = url_for('leave_troika', troika_id = troika_id, troika_role = troika_role))
    troika = get_troika(troika_id);
    user = get_user(session['email'])
    if troika.get_phase() != 'complete':
        if troika_role == '0':
            if troika.teacher != user:
                flash('You are not the teacher of this Troika.', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.teacher = None
            save_troika(troika)
            flash('You are no longer teaching "' + troika.title +  '".')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '1':
            if troika.first_learner != user:
                flash('You are not the first learner of this Troika.', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.first_learner = None
            save_troika(troika)
            flash('You are no longer the first learner of "' + troika.title +  '".')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '2':
            if troika.second_learner != user:
                flash('You are not the second learner of this Troika.', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.second_learner = None
            save_troika(troika)
            flash('You are no longer the second learner of "' + troika.title +  '".')
            return redirect(url_for('troika', troika_id=troika_id))
        elif troika_role == '3':
            if user not in troika.participants:
                flash('You are not participating in the Troika', 'error')
                return redirect(url_for('troika', troika_id=troika_id))
            troika.participants.remove(user)
            save_troika(troika)
            flash('You are no longer participating in "' + troika.title +  '".')
            return redirect(url_for('troika', troika_id=troika_id))
            
        else:
            flash('Unknown Troika role: ' + troika_role, 'error')
            return redirect(url_for('troika', troika_id=troika_id))
    else:
        flash('You can not leave a Troika that is complete', 'error')
        return redirect(url_for('troika', troika_id=troika_id))


@app.route('/create', methods=['GET', 'POST'])
def create_troika():
    __check_login('create_troika')
    troikaerrors = []
    troikaform = TroikaForm(prefix="troika")
    # Find out if the logged in user has rights to edit/delete
    user = get_user(session['email'])

    start_time = __get_start_datetime(troikaform.start_date.data, troikaform.start_time_hours.data, troikaform.start_time_minutes.data)
    if troikaform.validate_on_submit():
        troika = Troika(created=datetime.datetime.now(), 
                title=troikaform.title.data,
                description=troikaform.description.data,
                country='FI', region='18', area_id=None, campus_id=None,
                address=troikaform.address.data,
                address_addendum=troikaform.address_addendum.data,
                language='fi', 
                start_time=start_time,
                end_time=__get_end_datetime(start_time, troikaform.duration.data),
                max_participants=troikaform.max_participants.data, 
                creator=user)        
        if troikaform.creator_is_teacher.data:
            troika.teacher = user
        else:
            troika.first_learner = user
        save_troika(troika)
        return redirect(url_for('troika', troika_id=troika.id))
        flash('Troika Created')
    if troikaform.errors:
        for key, value in troikaform.errors.items():
            troikaerrors.append(key + ': ' + value[0])
    return render_template('edit_troika.html', 
                           troikaform=troikaform, troikaerrors=troikaerrors,
                           access='create')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    flash('You were logged out')
    return redirect(url_for('troikas'))
