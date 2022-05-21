# -*- coding: utf-8 -*-

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License (the "License")
# You may not use this file except in
# compliance with the License. A copy of the License is located at http://aws.amazon.com/asl/
#
# This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific
# language governing permissions and limitations under the License.


import json

import logging

from response import AlexaResponse

import jwt
import requests
import datetime
import colorsys

SECRET = 'R1BhE53$yt76$RR1hB5YJM'
URL = 'https://retropixelapi.herokuapp.com'
#token = jwt.encode({"token_type": "access","user": "164521328368ddfbf9eac4cc94","exp":datetime.datetime.now() + datetime.timedelta(hours=24)}, SECRET, algorithm="HS256")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(request, context):

    # Dump the request for logging - check the CloudWatch logs.
    print('lambda_handler request  -----')
    print(json.dumps(request))


    if context is not None:
        print('lambda_handler context  -----')
        print(context)

    # Validate the request is an Alexa smart home directive.
    if 'directive' not in request:
        alexa_response = AlexaResponse(
            name='ErrorResponse',
            payload={'type': 'INVALID_DIRECTIVE',
                     'message': 'Missing key: directive, Is the request a valid Alexa Directive?'})
        return send_response(alexa_response.get())

    # Check the payload version.
    payload_version = request['directive']['header']['payloadVersion']
    if payload_version != '3':
        alexa_response = AlexaResponse(
            name='ErrorResponse',
            payload={'type': 'INTERNAL_ERROR',
                     'message': 'This skill only supports Smart Home API version 3'})
        return send_response(alexa_response.get())

    # Crack open the request to see the request.
    name = request['directive']['header']['name']
    namespace = request['directive']['header']['namespace']

    # Handle the incoming request from Alexa based on the namespace.
    if namespace == 'Alexa.Authorization':
        if name == 'AcceptGrant':
            # Note: This example code accepts any grant request.
            # In your implementation, invoke Login With Amazon with the grant code to get access and refresh tokens.
            grant_code = request['directive']['payload']['grant']['code']
            grantee_token = request['directive']['payload']['grantee']['token']
            auth_response = AlexaResponse(namespace='Alexa.Authorization', name='AcceptGrant.Response')
            return send_response(auth_response.get())

    if namespace == 'Alexa':
        if name == 'ReportState':
            token = request['directive']['endpoint']['scope']['token']
            endpoint_id = request['directive']['endpoint']['endpointId']
            correlation_token = request['directive']['header']['correlationToken']
            discovery_response = AlexaResponse(namespace='Alexa', name='StateReport', token=token, endpoint_id=endpoint_id, correlation_token=correlation_token)
            #discovery_response.add_context_property(namespace='Alexa.EndpointHealth', name='connectivity', value={'value': 'UNREACHABLE','reason':'INTERNET_UNREACHABLE'})
            discovery_response.add_context_property(namespace='Alexa.EndpointHealth', name='connectivity', value={'value': 'OK'})
            discovery_response.add_context_property(namespace='Alexa.PowerController', name='powerState', value='OFF')
            discovery_response.add_context_property(namespace='Alexa.ColorController', name='color', value={"hue": 120, "saturation": 1, "brightness": 1})
            return send_response(discovery_response.get())

    if namespace == 'Alexa.Discovery':
        if name in ['Discover', 'Discover.Response']:
            token = request['directive']['payload']['scope']['token']
            device_list, device_names = get_devices(token)
            # The request to discover the devices the skill controls.
            discovery_response = AlexaResponse(namespace='Alexa.Discovery', name='Discover.Response')
            # Create the response and add the light bulb capabilities.
            capability_alexa = discovery_response.create_payload_endpoint_capability()
            capability_alexa_powercontroller = discovery_response.create_payload_endpoint_capability(
                interface='Alexa.PowerController',
                supported=[{'name': 'powerState'}])
            capability_alexa_colorcontroller = discovery_response.create_payload_endpoint_capability(
                interface='Alexa.ColorController',
                supported=[{'name': 'color'}])
            capability_alexa_endpointhealth = discovery_response.create_payload_endpoint_capability(
                interface='Alexa.EndpointHealth',
                supported=[{'name': 'connectivity'}])
            
            for device in device_list:
                discovery_response.add_payload_endpoint(
                    friendly_name=device_names[device]['name'],
                    endpoint_id=device,
                    capabilities=[capability_alexa, capability_alexa_endpointhealth, capability_alexa_colorcontroller, capability_alexa_powercontroller])
            discovery_response.add_context_property(namespace='Alexa.EndpointHealth', name='connectivity', value='OK')
            discovery_response.add_context_property(namespace='Alexa.PowerController', name='powerState', value='ON')
            discovery_response.add_context_property(namespace='Alexa.ColorController', name='color', value={"hue": 360, "saturation": 1, "brightness": 1})
            return send_response(discovery_response.get())

    if namespace == 'Alexa.ColorController':
        # The directive to TurnOff or TurnOn the light bulb.
        # Note: This example code always returns a success response.
        token = request['directive']['endpoint']['scope']['token']
        endpoint_id = request['directive']['endpoint']['endpointId']
        color_state_value = request['directive']['payload']['color']
        correlation_token = request['directive']['header']['correlationToken']
        color = hsl_to_int(color_state_value)
        # Check for an error when setting the state.
        device_set = update_device_state(endpoint_id=endpoint_id, state='color', value=color)
        if not device_set:
            return AlexaResponse(
                name='ErrorResponse',
                payload={'type': 'ENDPOINT_UNREACHABLE', 'message': 'Unable to reach endpoint database.'}).get()

        directive_response = AlexaResponse(correlation_token=correlation_token)
        directive_response.add_context_property(namespace='Alexa.ColorController', name='color', value=color_state_value)
        return send_response(directive_response.get())
        
    if namespace == 'Alexa.PowerController':
        # The directive to TurnOff or TurnOn the light bulb.
        # Note: This example code always returns a success response.
        token = request['directive']['endpoint']['scope']['token']
        endpoint_id = request['directive']['endpoint']['endpointId']
        power_state_value = 'OFF' if name == 'TurnOff' else 'ON'
        correlation_token = request['directive']['header']['correlationToken']

        # Check for an error when setting the state.
        device_set = update_device_state(endpoint_id=endpoint_id, state='powerState', value=power_state_value, token=token)
        if not device_set:
            return AlexaResponse(
                name='ErrorResponse',
                payload={'type': 'ENDPOINT_UNREACHABLE', 'message': 'Unable to reach endpoint database.'}).get()

        directive_response = AlexaResponse(correlation_token=correlation_token)
        directive_response.add_context_property(namespace='Alexa.PowerController', name='powerState', value=power_state_value)
        return send_response(directive_response.get())

# Send the response
def send_response(response):
    print('lambda_handler response -----')
    print(json.dumps(response))
    return response

# Make the call to your device cloud for control
def update_device_state(endpoint_id, state, value, token):
    if state == 'powerState':
        topic = f'{endpoint_id}/OnOff'
        payload = 'true' if value == 'ON' else 'false'
    if state == 'color':
        topic = f'{endpoint_id}/Color'
        payload = str(value)

    response = requests.get(f"{URL}/set?topic={topic}&payload={payload}",
        headers={'Authorization': f'Bearer {token}'}
    )
    # attribute_key = state + 'Value'
    # result = stubControlFunctionToYourCloud(endpointId, token, request);
    return True

def get_devices(token):
    response = requests.get(f"{URL}/devices",
            headers={'Authorization': f'Bearer {token}'}
        )
    results = response.json()
    return results['list'], results['states']

def hsl_to_int(color):
    hue = float(color["hue"]/360)
    saturation = float(color["saturation"])
    brightness = float(color["brightness"])
    rgb = colorsys.hsv_to_rgb(hue, saturation, brightness)
    hex = '0x'+''.join(["%0.2X" % int(255*c) for c in rgb])
    return int(hex, base=16)
#update_device_state('', 'powerState', 'OFF')
#get_devices()

#print(hsl_to_int({"hue":360,"saturation":1,"brightness":1}))