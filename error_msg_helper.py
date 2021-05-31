from flask import Blueprint, request, abort, jsonify, make_response

from google.cloud import datastore
import json


import constants

def send_json_msg(msg, status_code, mime_type):
    res = make_response(json.dumps(msg))
    res.status_code = status_code
    res.mimetype = mime_type
    return res