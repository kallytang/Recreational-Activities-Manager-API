
from flask import Blueprint, request, abort, jsonify, make_response, session 

from google.cloud import datastore
import json
from datetime import datetime
import constants

bp = Blueprint('attendees', __name__, url_prefix='/attendees')

client = datastore.Client()


@bp.route("/", methods=['POST', 'GET'],  strict_slashes=False)
def get_post_attendees():
    return 0




@bp.route('/<id>', methods=['PUT','PATCH', 'DELETE','GET'])
def put_delete_get_attendee():
    return 0