from flask import Blueprint, request, abort, jsonify, make_response, session
import json
from datetime import datetime
from constants import *
from error_msg_helper import *
from helper_functions import *
from auth_helper import *
from google.cloud import datastore
import attendee

bp = Blueprint('activities', __name__, url_prefix='/activities')

client = datastore.Client()


@bp.route("/", methods=['POST', 'GET'], strict_slashes=False)
def get_post_activities():
    if request.method == 'POST':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload
        content = request.get_json()

        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

        else:
            # check if data sent by user is application/json
            if request.content_type != APPLICATION_JSON:
                return send_json_msg(UNSUPPORTED_MEDIA, 415, APPLICATION_JSON)

            content = request.get_json()

            if content:
                # check if content has extraneous fields or missing fields
                if NAME in content.keys() and DESCRIPTION in content.keys() and START in content.keys() and \
                        END in content.keys() and ROOM in content.keys() and PUBLIC in content.keys():

                    #  check if a field is missing
                    if len(content.keys()) > 6:
                        return send_json_msg(ACTIVITY_EXTRA_ATTR_MSG, 400, APPLICATION_JSON)

                    #     check if the content is a valid type
                    if type(content[NAME]) != str or type(content[DESCRIPTION]) != str or type(content[START]) != int \
                            or type(content[END]) != int or type(content[ROOM]) != int or type(content[PUBLIC]) != bool:
                        return send_json_msg(INVALID_TYPE, 400, APPLICATION_JSON)

                    # strip the leading and ending spaces in description and name field
                    content[NAME] = content[NAME].strip()
                    content[DESCRIPTION] = content[DESCRIPTION].strip()

                    #   check if length of name is
                    if validate_length(5, 30, content[NAME]) is False:
                        return send_json_msg(INVALID_NAME_LENGTH, 400, APPLICATION_JSON)

                    # check if the length of description is at least 5 characters long and at most 50 characters
                    if validate_length(5, 50, content[DESCRIPTION]) is False:
                        return send_json_msg(INVALID_DESC_LENGTH, 400, APPLICATION_JSON)

                    if validate_date(content[START], content[END]) is False:
                        return send_json_msg(INVALID_TIME_CHOICES, 400, APPLICATION_JSON)

                    if content[ROOM] < 1 or content[ROOM] > 300:
                        return send_json_msg(INVALID_ROOM_NUMBER, 403, APPLICATION_JSON)
                    # check if start is less than end

                    if room_available(content[ROOM], content[START], content[END]) is False:
                        return send_json_msg(ROOM_OVERLAP, 403, APPLICATION_JSON)

                    post_activity = datastore.entity.Entity(key=client.key(ACTIVITIES))
                    post_activity.update({
                        NAME: content[NAME],
                        DESCRIPTION: content[DESCRIPTION],
                        START: content[START],
                        END: content[END],
                        ROOM: content[ROOM],
                        INSTRUCTOR: payload[SUB],
                        PUBLIC: content[PUBLIC]
                    })
                    client.put(post_activity)
                    post_activity["id"] = str(post_activity.key.id)
                    post_activity["self"] = request.url + "/" + str(post_activity.key.id)
                    return send_json_msg(post_activity, 201, APPLICATION_JSON)
                else:
                    return send_json_msg(MISSING_ATTR, 400, APPLICATION_JSON)

    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)
        #  if there's a valid jwt only show user's JWT including private activities
        if 'Authorization' not in request.headers.keys():
            return get_activities_paginated(True, None)
        else:
            payload = verify_jwt(request)
            if type(payload) is not dict:
                return get_activities_paginated(True, None)
            else:
                return get_activities_paginated(False, payload[SUB])

    else:
        res = make_response(json.dumps({"Error": "Method not recognized"}))
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set("Allow", "POST, GET")
        return res


@bp.route('/<id>', methods=['PUT', 'PATCH', 'DELETE', 'GET'])
def put_patch_delete_get_activity(id):
    if request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)
        else:
            activity_key = client.key(ACTIVITIES, int(id))
            activity_item = client.get(key=activity_key)

            if activity_item is None:
                return send_json_msg(INVALID_ACTIVITY_ID, 404, APPLICATION_JSON)

            activity_item["id"] = str(activity_key.id)
            activity_item["self"] = request.url
            if ATTENDEE_LIST in  activity_item.keys():
                if len(activity_item[ATTENDEE_LIST]) > 0:
                    for item in activity_item[ATTENDEE_LIST]:
                        item["self"] = request.url_root + "attendees/" + item[ATTENDEE_ID]

            # todo  add list of attendee info
            if activity_item[PUBLIC] is False:
                if 'Authorization' not in request.headers.keys():
                    return send_json_msg(ERR_PRIVATE_ACTIVITY, 403)
                else:
                    payload = verify_jwt(request)
                    if type(payload) is not dict:
                        return send_json_msg(ERR_PRIVATE_ACTIVITY, 403)
                    if payload[SUB] != activity_item[INSTRUCTOR]:
                        return send_json_msg(ERR_PRIVATE_ACTIVITY, 403)

            return send_json_msg(activity_item, 200, APPLICATION_JSON)

    elif request.method == 'DELETE':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401

        payload = verify_jwt(request)
        if type(payload) is not dict:
            return payload

        activity_key = client.key(ACTIVITIES, int(id))
        activity_item = client.get(key=activity_key)
        if activity_item is None:
            return send_json_msg(INVALID_ACTIVITY_ID, 404, APPLICATION_JSON)

        # check if the activity is associated with client id
        if payload[SUB] != activity_item[INSTRUCTOR]:
            return send_json_msg(ACTIVITY_WRONG_USER, 403, APPLICATION_JSON)
        #  if no attendees, delete the activity
        if ALL_ATTENDEES not in activity_item.keys():
            client.delete(activity_key)
            return '', 204

    else:
        res = make_response(json.dumps({"Error": "Method not recognized"}))
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set("Allow", "PUT, PATCH, DELETE, GET")
        return res


@bp.route('/<activity_id>/attendees/<attendee_id>', methods=['PUT', 'PATCH', 'DELETE', 'GET'])
def add_remove_attendee(activity_id, attendee_id):
    if request.method == 'PUT':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401
        else:
            payload = verify_jwt(request)
            if type(payload) is not dict:
                return payload

            if 'application/json' not in request.accept_mimetypes:
                return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

            activity_key = client.key(ACTIVITIES, int(activity_id))
            activity_item = client.get(key=activity_key)
            attendee_key = client.key(ATTENDEES, int(attendee_id))
            attendee_item = client.get(key=attendee_key)
            # if activity and/or attendee does not exist, send an error message
            if attendee_item is None or activity_item is None:
                print(attendee_item)
                print(activity_item)
                send_json_msg(INVALID_ATTENDEE_ACTIVITY_ID, 404, APPLICATION_JSON)

            # check if user is authorized to make changes to this class
            if payload[SUB] != activity_item[INSTRUCTOR]:
                send_json_msg(UNAUTH_TO_ADD, 403, APPLICATION_JSON)


            # add activity id to attendee list of activities_list
            if ACTIVITY_LIST not in attendee_item.keys():
                attendee_item[ACTIVITY_LIST] = [{ACTIVITY_ID: activity_id,
                                                 NAME: activity_item[NAME]}]
            else:
                # check if activity already exists with attendee
                if len(attendee[ACTIVITY_LIST]) > 0:
                    for items in attendee[ACTIVITY_LIST]:
                        if activity_id == attendee_id[ACTIVITY_ID]:
                            return send_json_msg(ATTENDEE_ALREADY_EXISTS, 403, APPLICATION_JSON)

                attendee_id[ACTIVITY_LIST].append({ACTIVITY_ID: activity_id,
                                                   NAME: activity_item[NAME]})

            #  add attendee to activity list
            if ATTENDEE_LIST not in attendee_item.keys():
                activity_item[ATTENDEE_LIST] = [{ATTENDEE_ID: attendee_id}]

            else:
                activity_item[ATTENDEE_LIST].append({ATTENDEE_ID: attendee_id})

            # store change in datastore
            client.put(activity_item)
            client.put(attendee_item)
            return "", 204
    # removing attendee from activity
    elif request.method == 'DELETE':
        if 'Authorization' not in request.headers.keys():
            return jsonify(MISSING_TOKEN), 401
        else:
            payload = verify_jwt(request)
            if type(payload) is not dict:
                return payload

            if 'application/json' not in request.accept_mimetypes:
                return send_json_msg(NOT_SUPPORTED, 406, APPLICATION_JSON)

            activity_key = client.key(ACTIVITIES, int(activity_id))
            activity_item = client.get(key=activity_key)
            attendee_key = client.key(ATTENDEES, int(attendee_id))
            attendee_item = client.get(key=attendee_key)
            # if activity and/or attendee does not exist, send an error message
            if attendee_item is None or activity_item is None:
                print(attendee_item)
                print(activity_item)
                send_json_msg(INVALID_ATTENDEE_ACTIVITY_ID, 404, APPLICATION_JSON)

            # check if user is authorized to make changes to this class
            if payload[SUB] != activity_item[INSTRUCTOR]:
                send_json_msg(UNAUTH_TO_ADD, 403, APPLICATION_JSON)

            if ACTIVITY_LIST not in attendee_item.keys():
                send_json_msg(ATTENDEE_NOT_IN_ACTIVITY, 403, APPLICATION_JSON)

            else:
                was_registered = False
                # find if the attendee exists
                for i in range(len(activity_item[ATTENDEE_LIST])):
                    was_registered = True
                    if activity_item[ATTENDEE_LIST][i][ATTENDEE_ID] == attendee_id:
                        activity_item[ATTENDEE_LIST].pop(i)
                        #  remove the activity from the attendee
                        for idx in range(len(attendee_item[ACTIVITY_LIST])):
                            if attendee_item[ACTIVITY_LIST][idx][ACTIVITY_ID] == activity_id:
                                attendee_item[ACTIVITY_LIST].pop(idx)
                        #  update items
                        client.put(attendee_item)
                        client.put(activity_item)

                if was_registered:
                    return "", 204
                else:
                    return send_json_msg(ATTENDEE_NOT_IN_ACTIVITY, 403, APPLICATION_JSON)

    else:

        res = make_response(json.dumps({"Error": "Method not recognized"}))
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set("Allow", "PUT, PATCH, DELETE, GET")
        return res


def get_activities_paginated(public: bool, user):
    #   return public activities
    query_all = client.query(kind=ACTIVITIES)

    if public is True:
        query_all.add_filter(PUBLIC, "=", True)
    if user:
        query_all.add_filter(INSTRUCTOR, "=", user)
    results_no_pagination = list(query_all.fetch())
    num_activities = len(results_no_pagination)
    # add pagination
    q_limit = int(request.args.get('limit', 5))
    q_offset = int(request.args.get("offset", 0))
    page_iterator = query_all.fetch(limit=q_limit, offset=q_offset)
    pages = page_iterator.pages
    results = list(next(pages))
    data_to_send = {}
    if page_iterator.next_page_token:
        next_offset = q_offset + q_limit
        next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        data_to_send["next"] = next_url
        data_to_send["count"] = num_activities
    else:
        next_url = None
        data_to_send["next"] = next_url
        data_to_send["count"] = num_activities

    if len(results) == 0:
        return jsonify(results)

    for item in results:
        if ATTENDEE_LIST in item.keys():
            item[NUM_ATTENDEES] = len(item[NUM_ATTENDEES])
        item["id"] = str(item.key.id)
        item["self"] = request.url + "/" + str(item.key.id)

    data_to_send[ACTIVITIES] = results

    return send_json_msg(data_to_send, 200, APPLICATION_JSON)
