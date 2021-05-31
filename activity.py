
from flask import Blueprint, request, abort, jsonify, make_response, session

from google.cloud import datastore
import json
from datetime import datetime
import constants

bp = Blueprint('activities', __name__, url_prefix='/activities')

bp.route("", strict_slashes=False)

client = datastore.Client()

