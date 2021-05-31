from flask import Blueprint, request, abort, jsonify, make_response

from google.cloud import datastore
import json
from datetime import datetime
import constants

import requests

from functools import wraps
import json

from six.moves.urllib.request import urlopen
from flask_cors import cross_origin
from jose import jwt

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
# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            # Redirect to Login page here
            return redirect('/')
        return f(*args, **kwargs)

    return decorated


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


def verify_jwt(request):
    auth_header = request.headers['Authorization'].split();
    token = auth_header[1]
    jsonurl = urlopen("https://" + DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        return handle_auth_error(AuthError({"code": "invalid_header",
                                            "description":
                                                "Invalid header. "
                                                "Use an RS256 signed JWT Access Token"}, 401))
    if unverified_header["alg"] == "HS256":
        return handle_auth_error(AuthError({"code": "invalid_header",
                                            "description":
                                                "Invalid header. "
                                                "Use an RS256 signed JWT Access Token"}, 401))
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://" + DOMAIN + "/"
            )
        except jwt.ExpiredSignatureError:
            return handle_auth_error(AuthError({"code": "token_expired",
                                                "description": "token is expired"}, 401))
        except jwt.JWTClaimsError:
            return handle_auth_error(AuthError({"code": "invalid_claims",
                                                "description":
                                                    "incorrect claims,"
                                                    " please check the audience and issuer"}, 401))
        except Exception:
            return handle_auth_error(AuthError({"code": "invalid_header",
                                                "description":
                                                    "Unable to parse authentication"
                                                    " token."}, 401))

        return payload
    else:
        return handle_auth_error(AuthError({"code": "no_rsa_key",
                                            "description":
                                                "No RSA key in JWKS"}, 401))



