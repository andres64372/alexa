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
            discovery_response.add_context_property(namespace='Alexa.PowerController', name='powerState', value='ON')
            discovery_response.add_context_property(namespace='Alexa.ColorController', name='color', value={"hue": 360, "saturation": 1, "brightness": 1})
            return send_response(discovery_response.get())

    if namespace == 'Alexa.Discovery':
        if name in ['Discover', 'Discover.Response']:
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
            discovery_response.add_payload_endpoint(
                friendly_name='Luz',
                endpoint_id='sample-bulb-01',
                capabilities=[capability_alexa, capability_alexa_endpointhealth, capability_alexa_colorcontroller, capability_alexa_powercontroller])
            token = request['directive']['payload']['scope']['token']
            discovery_response.add_context_property(namespace='Alexa.PowerController', name='powerState', value='ON')
            discovery_response.add_context_property(namespace='Alexa.ColorController', name='color', value={"hue": 360, "saturation": 1, "brightness": 1})
            return send_response(discovery_response.get())

    if namespace == 'Alexa.ColorController':
        # The directive to TurnOff or TurnOn the light bulb.
        # Note: This example code always returns a success response.
        endpoint_id = request['directive']['endpoint']['endpointId']
        color_state_value = request['directive']['payload']['color']
        correlation_token = request['directive']['header']['correlationToken']

        # Check for an error when setting the state.
        device_set = update_device_state(endpoint_id=endpoint_id, state='color', value=color_state_value)
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
        endpoint_id = request['directive']['endpoint']['endpointId']
        power_state_value = 'OFF' if name == 'TurnOff' else 'ON'
        correlation_token = request['directive']['header']['correlationToken']

        # Check for an error when setting the state.
        device_set = update_device_state(endpoint_id=endpoint_id, state='powerState', value=power_state_value)
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
def update_device_state(endpoint_id, state, value):
    # attribute_key = state + 'Value'
    # result = stubControlFunctionToYourCloud(endpointId, token, request);
    return True