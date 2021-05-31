
from flask import Blueprint, request, abort, jsonify, make_response, session 

from google.cloud import datastore
import json
from datetime import datetime
import constants

bp = Blueprint('load', __name__, url_prefix='/loads')

bp.route("", strict_slashes=False)


client = datastore.Client()
