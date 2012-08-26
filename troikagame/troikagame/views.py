'''
Created on 14.8.2012

@author: ttiurani
'''
from troikagame import app
from security import validate_login
from backend import *
from flask import request, session, flash, redirect, url_for, render_template

@app.route('/about')
def about():
    return 'About'

@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % username

@app.route('/')
def show_troikas():
    active_troikas = get_active_troikas()
    active_entries = [dict(start_time=active_troika.start_time, 
                    title=active_troika.title, 
                    description=active_troika.description) 
               for active_troika in active_troikas]
    pending_troikas = get_pending_troikas()
    pending_entries = [dict(start_time=pending_troika.start_time, 
                    title=pending_troika.title, 
                    description=pending_troika.description) 
               for pending_troika in pending_troikas]
    completed_troikas = get_completed_troikas()
    completed_entries = [dict(start_time=completed_troika.start_time, 
                    title=completed_troika.title, 
                    description=completed_troika.description) 
               for completed_troika in completed_troikas]
    return render_template('show_troikas.html', 
                           active_entries=active_entries,
                           pending_entries=pending_entries,
                           completed_entries=completed_entries)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if (validate_login(request.form['email'], request.form['password'])):
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_troikas'))
        else:
            error = 'Invalid email/password'
  
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_troikas'))
