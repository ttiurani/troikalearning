#  Copyright (c) 2012 Timo Tiuraniemi
#
#  This file is part of Troika.
#
#  Troika is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, see http://www.gnu.org/licenses
#

'''
Created on 14.8.2012

@author: ttiurani
'''

from troikalearning import _
from troikalearning.backend import User, save_user, get_user, get_user_by_reset_key
from passlib.hash import sha256_crypt
from flask import request, url_for, flash
from urlparse import urlparse, urljoin

import os
from datetime import datetime
from datetime import timedelta as dttimedelta

def validate_login(email, password):
    # First get the user from the backend based on email
    user = get_user(email)
    if user is not None:
        if (__validate_password(password, user.password)):
            return user
    return False

def register(first_name, last_name, alias, email, password):
    hash = hash_password(password)
    user = User(email=email, role='user', 
             password=hash,
             country='FI', region='18', preferred_language='fi',
             full_name=first_name + " " + last_name, short_name=first_name, 
             given_names=first_name, family_name=last_name, alias=alias)
    save_user(user)
    
def hash_password(password):
    return sha256_crypt.encrypt(password)

def get_troika_access_right(user, troika):
    access = False
    if user.role == 'admin':
        # Admin can always do anything he wants
        access = 'delete'
    elif troika.get_phase() is not 'complete':
        if user == troika.creator:
            # Creator can delete non-completed Troikas
            access = 'delete'
        elif user == troika.lead:
            # Lead can edit Troika contents
            access = 'edit'
    return access

def activation_ready(troika):
    if (troika.address is not None and 
        troika.start_time is not None and 
        troika.end_time is not None and 
        troika.activated is None and
        troika.lead is not None and
        troika.first_learner is not None and
        troika.second_learner is not None):
        return True
    return False

def activatable(user, troika, activatable_before_three):

    if ((user.role == "admin" or troika.creator is user or troika.lead is user) and  
        troika.address is not None and 
        troika.start_time is not None and 
        troika.end_time is not None and 
        troika.activated is None):
        if activatable_before_three or user.role == "admin":
            return True
        else:
            # Also make sure there are three participants
            if (troika.lead is not None and
                troika.first_learner is not None and
                troika.second_learner is not None):
                return True
    return False

def __validate_password(plain_password, password_hash):
    return sha256_crypt.verify(plain_password, password_hash)

def __generate_reload_token():
    return os.urandom(32);

# From http://flask.pocoo.org/snippets/62/

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target
    flash(_(u'Invalid redirect target'), 'error')
    return url_for('troikas')

def generate_password_reset_link(email):
    user = get_user(email)
    if user is None:
        return None
    reset_key = os.urandom(16).encode('hex')
    user.password_reset_key = reset_key
    user.password_reset_expire = datetime.now() + dttimedelta(minutes=60)
    save_user(user)
    return url_for('reset', reset_key = reset_key, _external=True)
