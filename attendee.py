from flask import Blueprint, request, abort, jsonify, make_response, session

from google.cloud import datastore
import json
from datetime import datetime
from constants import *
from helper_functions import *
from auth_helper import *
from error_msg_helper import *

bp = Blueprint('attendees', __name__, url_prefix='/attendees')

client = datastore.Client()


@bp.route("/", methods=['POST', 'GET'], strict_slashes=False)
def get_post_attendees():
    if request.method == 'POST':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload

        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

        else:
            # check if data sent by user is application/json
            if request.content_type != APPLICATION_JSON:
                return send_json_msg(UNSUPPORTED_MEDIA, 415, APPLICATION_JSON)

            content = request.get_json()

            # check if the content is valid
            if content:
                if FIRST_NAME in content.keys() and LAST_NAME in content.keys() and EMAIL in content.keys() \
                        and PHONE in content.keys():
                    if len(content.keys()) > 4:
                        return send_json_msg(ACTIVITY_EXTRA_ATTR_MSG, 400, APPLICATION_JSON)
                    if type(content[FIRST_NAME]) != str or type(content[LAST_NAME]) != str or \
                            type(content[PHONE]) != int or type(content[EMAIL]) != str:
                        return send_json_msg(INVALID_TYPE, 400, APPLICATION_JSON)

                    # check if the phone is a valid length 10 digits
                    if len(str(content[PHONE])) != 10:
                        return send_json_msg(ERR_PHONE_LEN, 400, APPLICATION_JSON)

                    # check if the account already exists
                    query = client.query(kind=ATTENDEES)
                    query.add_filter(PHONE, "=", content[PHONE])
                    query.add_filter(FIRST_NAME, "=", content[FIRST_NAME])
                    query.add_filter(LAST_NAME, "=", content[LAST_NAME])
                    query.add_filter(EMAIL, "=", content[EMAIL])
                    curr_attendees = list(query.fetch())
                    if curr_attendees:
                        return send_json_msg(ATTENDEE_NOT_UNIQUE, 403, APPLICATION_JSON)

                    post_attendee = datastore.entity.Entity(key=client.key(ATTENDEES))
                    post_attendee.update({
                        FIRST_NAME: content[FIRST_NAME],
                        LAST_NAME: content[LAST_NAME],
                        EMAIL: content[EMAIL],
                        PHONE: content[PHONE]
                    })
                    client.put(post_attendee)
                    post_attendee["id"] = str(post_attendee.key.id)
                    post_attendee["self"] = request.url + "/" + str(post_attendee.key.id)
                    return send_json_msg(post_attendee, 201, APPLICATION_JSON)
                else:
                    return send_json_msg(MISSING_ATTR, 400, APPLICATION_JSON)
            else:
                return send_json_msg(MISSING_ATTR, 400, APPLICATION_JSON)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)
        if "limit" in request.args.keys():
            if request.args.get("limit").isnumeric() is not True:
                return send_json_msg(OFFSET_LIMIT_INVALID, 400, APPLICATION_JSON)
        if "offset" in request.args.keys():
            if request.args.get("offset").isnumeric() is not True:
                return send_json_msg(OFFSET_LIMIT_INVALID, 400, APPLICATION_JSON)
        query = client.query(kind=ATTENDEES)
        results_no_limit = list(query.fetch())
        count = len(results_no_limit)
        q_limit = int(request.args.get('limit', 5))
        q_offset = int(request.args.get("offset", 0))
        page_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = page_iterator.pages
        results = list(next(pages))
        data_to_send = {}
        if page_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            data_to_send["next"] = next_url
            data_to_send["count"] = count
        else:
            next_url = None
            data_to_send["next"] = next_url
            data_to_send["count"] = count

        if len(results) == 0:
            return jsonify(results)

        for item in results:
            item["id"] = str(item.key.id)
            item["self"] = request.url + "/" + str(item.key.id)
            if ACTIVITY_LIST in item.keys():
                item[NUM_ACTIVITIES] = len(item[ACTIVITY_LIST])
                if len(item[ACTIVITY_LIST]) > 0:
                    for item_activity in item[ACTIVITY_LIST]:
                        item_activity["self"] = request.url_root + "activities/" + item_activity[ACTIVITY_ID]

        data_to_send[ATTENDEES] = results

        return send_json_msg(data_to_send, 200, APPLICATION_JSON)
    else:
        res = make_response(json.dumps({"Error": "Method not recognized"}))
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set("Allow", "POST, GET")
        return res


@bp.route('/<id>', methods=['PUT', 'PATCH', 'DELETE', 'GET'])
def put_delete_get_attendee(id):
    if request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)
        else:
            attendee_key = client.key(ATTENDEES, int(id))
            attendee_item = client.get(key=attendee_key)

            if attendee_item is None:
                return send_json_msg(INVALID_ATTENDEE_ID, 404, APPLICATION_JSON)

            if ACTIVITY_LIST in attendee_item.keys():
                attendee_item[NUM_ACTIVITIES] = len(attendee_item[ACTIVITY_LIST])
            attendee_item["id"] = str(attendee_key.id)
            attendee_item["self"] = request.url + "/" + str(attendee_key.id)
            if ACTIVITY_LIST in attendee_item.keys():
                attendee_item[NUM_ACTIVITIES] = len(attendee_item[ACTIVITY_LIST])
                if len(attendee_item[ACTIVITY_LIST]) > 0:
                    for item_activity in attendee_item[ACTIVITY_LIST]:
                        item_activity["self"] = request.url_root + "activities/" + item_activity[ACTIVITY_ID]
            # request.url_root + "attendee/" + id
            return send_json_msg(attendee_item, 200, APPLICATION_JSON)
    elif request.method == 'DELETE':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload

        # first check if item exists
        attendee_key = client.key(ATTENDEES, int(id))
        attendee_item = client.get(key=attendee_key)

        if attendee_item is None:
            return send_json_msg(INVALID_ATTENDEE_ID, 404, APPLICATION_JSON)

        #     check if there's a list of classes that the attendee has taken
        if ACTIVITY_LIST not in attendee_item.keys():
            client.delete(attendee_key)
            return "", 204

        # if the attendee has at least one activity attending then return an error that user must be removed from
        if len(attendee_item[ACTIVITY_LIST]) > 0:
            #  for loop to remove all items that have attendee registered
            for activity_item in attendee_item[ACTIVITY_LIST]:
                remove_activity_key = client.key(ACTIVITIES, int(activity_item[ACTIVITY_ID]))
                remove_activity = client.get(key=remove_activity_key)
                delete_index = -1
                for idx in range(len(remove_activity[ATTENDEE_LIST])):
                    if remove_activity[ATTENDEE_LIST][idx][ATTENDEE_ID] == id:
                        delete_index = idx
                if delete_index >= 0:
                    remove_activity[ATTENDEE_LIST].pop(delete_index)
                    client.put(remove_activity)

        client.delete(attendee_key)
        return "", 204

    # must PUT method will remove the attendee from activities registered
    elif request.method == 'PUT':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload

        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

        # check if attendee exists
        attendee_key = client.key(ATTENDEES, int(id))
        attendee_item = client.get(key=attendee_key)
        if attendee_item is None:
            return send_json_msg(INVALID_ATTENDEE_ID, 404, APPLICATION_JSON)

        content = request.get_json()
        if content:
            if FIRST_NAME in content.keys() and LAST_NAME in content.keys() and EMAIL in content.keys() \
                    and PHONE in content.keys():
                if len(content.keys()) > 4:
                    return send_json_msg(ACTIVITY_EXTRA_ATTR_MSG, 400, APPLICATION_JSON)
                if type(content[FIRST_NAME]) != str or type(content[LAST_NAME]) != str or \
                        type(content[PHONE]) != int or type(content[EMAIL]) != str:
                    return send_json_msg(INVALID_TYPE, 400, APPLICATION_JSON)

                # check if the phone is a valid length 10 digits
                if len(str(content[PHONE])) != 10:
                    return send_json_msg(ERR_PHONE_LEN, 400, APPLICATION_JSON)

                # check if the fields entered is the same as another attendee in datastore
                # check if the account already exists
                    query = client.query(kind=ATTENDEES)
                    query.add_filter(PHONE, "=", content[PHONE])
                    query.add_filter(FIRST_NAME, "=", content[FIRST_NAME])
                    query.add_filter(LAST_NAME, "=", content[LAST_NAME])
                    query.add_filter(EMAIL, "=", content[EMAIL])
                    curr_attendees = list(query.fetch())
                    if curr_attendees:
                        # check if it is the same user or a different user
                        if len(curr_attendees) == 0:
                            # if the items are two different id's then return an error
                            if curr_attendees[0].key.id != id:
                                return send_json_msg(ATTENDEE_NOT_UNIQUE, 403, APPLICATION_JSON)


                #  if there's no activities associated with attendee, then update
                if ACTIVITY_LIST not in attendee_item.keys() or len(attendee_item[ACTIVITY_LIST]) == 0:
                    attendee_item.update({
                        FIRST_NAME: content[FIRST_NAME],
                        LAST_NAME: content[LAST_NAME],
                        EMAIL: content[EMAIL],
                        PHONE: content[PHONE]
                    })
                    client.put(attendee_item)
                    return "", 204

                # there's items that need to be removed
                else:
                    for activity_item in attendee_item[ACTIVITY_LIST]:
                        remove_activity_key = client.key(ACTIVITIES, int(activity_item[ACTIVITY_ID]))
                        remove_activity = client.get(key=remove_activity_key)
                        delete_index = -1
                        for idx in range(len(remove_activity[ATTENDEE_LIST])):
                            if remove_activity[ATTENDEE_LIST][idx][ATTENDEE_ID] == id:
                                delete_index = idx
                        if delete_index >= 0:
                            remove_activity[ATTENDEE_LIST].pop(delete_index)
                            client.put(remove_activity)

                    attendee_item.update({
                        FIRST_NAME: content[FIRST_NAME],
                        LAST_NAME: content[LAST_NAME],
                        EMAIL: content[EMAIL],
                        PHONE: content[PHONE]
                    })
                    client.put(attendee_item)

            else:
                return send_json_msg(MISSING_ATTR, 400, APPLICATION_JSON)
        else:
            return send_json_msg(MISSING_ATTR, 400, APPLICATION_JSON)

    elif request.method == 'PATCH':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload

        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

        # check if attendee exists
        attendee_key = client.key(ATTENDEES, int(id))
        attendee_item = client.get(key=attendee_key)
        if attendee_item is None:
            return send_json_msg(INVALID_ATTENDEE_ID, 404, APPLICATION_JSON)

    else:
        res = make_response(json.dumps({"Error": "Method not recognized"}))
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set("Allow", "PUT, PATCH, DELETE, GET")
        return res
