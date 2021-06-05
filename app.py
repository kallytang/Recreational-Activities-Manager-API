from google.cloud import datastore
from flask import Flask, request, jsonify, _request_ctx_stack
import requests

from functools import wraps
import json

from six.moves.urllib.request import urlopen
from flask_cors import cross_origin
from jose import jwt

import json
from os import environ as env
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from auth_helper import *
from constants import *

import attendee
import activity

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'

client = datastore.Client()

app.register_blueprint(attendee.bp)
# import bp from auth_helper file
app.register_blueprint(bp)
app.register_blueprint(activity.bp)

CALLBACK_URL = 'http://localhost:8080/callback'
# CALLBACK_URL = 'https://hw7-tangka.wl.r.appspot.com/callback'


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for("index", _external=True), 'client_id': CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))


@app.route('/logged_in', methods=['POST'])
def login_user_page():
    content = request.get_json()
    username = request.form["username"]
    password = request.form["password"]
    body = {'grant_type': 'password', 'username': username,
            'password': password,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
            }
    headers = {'content-type': 'application/json'}
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)
    json_body = {
        'name': username
    }
    return render_template('dashboard.html',
                           userinfo=json_body,
                           userinfo_pretty=json.dumps(r.json(), indent=4))


@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')


@app.route('/ui_login')
def ui_login():
    return auth0.authorize_redirect(redirect_uri=CALLBACK_URL)


@app.route('/login', methods=['POST'])
def login_user():
    content = request.get_json()
    username = content["username"]
    password = content["password"]
    body = {'grant_type': 'password', 'username': username,
            'password': password,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
            }
    headers = {'content-type': 'application/json'}
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)
    return r.text, 200, {'Content-Type': 'application/json'}


@app.route('/delete_all')
def delete_all_entities():
    query1 = client.query(kind=ACTIVITIES)
    query2 = client.query(kind=ATTENDEES)
    result1 = list(query1.fetch())
    result2 = list(query2.fetch())
    for item in result1:
        client.delete(item.key)

    for att in result2:
        client.delete(att.key)
    return "ok"


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)


# https://auth0.com/docs/users/user-search/retrieve-users-with-get-users-endpoint