
from flask import Blueprint, request, abort, jsonify, make_response, session

from google.cloud import datastore
import json
from datetime import datetime
from constants import *
from error_msg_helper import *

from auth_helper import *
bp = Blueprint('activities', __name__, url_prefix='/activities')


client = datastore.Client()
@bp.route("/", methods=['POST', 'GET'],  strict_slashes=False)
def get_post_activities():
    if request.method == 'POST':
        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

        else:
            # check if data sent by user is application/json
            if request.content_type != APPLICATION_JSON:
                return send_json_msg(UNSUPPORTED_MEDIA, 415, APPLICATION_JSON)

            content = request.get_json()
            # check if content has extraneous fields or missing fields


@bp.route('/<id>', methods=['PUT','PATCH', 'DELETE','GET'])
def put_patch_delete_get_activity():
    return 0




