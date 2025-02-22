'''
This file is the entry point for the worker process. It is responsible for
- Loading the user's lambda function
- Starting the HTTP server
- Handling requests from the controller
- Handling cache-put requests from other workers
- Sending the result back to the controller no matter the result is success or failure

Any exception catched by the worker within the given lambda_handler will be 
treated as a failure.
'''

import os
import sys
import importlib.util

import logging
import argparse
import logging
from flask import Flask, request, jsonify, make_response

from .storage import RedisDB
from .serverless_function import Metadata

lambda_file = None

lambda_handler = None

# Read from env.
redis_host = os.getenv('REDIS_HOST', '10.0.0.100')
redis_port = int(os.getenv('REDIS_PORT', 6379))

redis_proxy = RedisDB(host=redis_host, port=redis_port)


# logging
logger = logging.getLogger("lucas")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#flask
app = Flask(__name__)

@app.post('/')
def invoke():
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Failed to invoke the lambda function: {e}")
        return jsonify({'error': str(e)}), 500

    try:
        request_type = data['type']
    except KeyError:
        logger.error(f"Failed to invoke the lambda function: request type is missing")
        return jsonify({'error': 'request type is missing'}), 400
    
    if request_type == 'invoke':
        try:
            id = data['id']
            params = data['params']
            namespace = data['namespace']
            router = data['router']

            metadata = Metadata(
                id=id,
                params=params,
                namespace=namespace,
                router=router,
                request_type=request_type,
                redis_db=redis_proxy
            )
            logger.info(f"Invoking the lambda function with metadata: {metadata}")

            result = lambda_handler(metadata)
            return jsonify({
                'status': 'ok',
                'data': result
            })
        except Exception as e:
            logger.error(f"Failed to invoke the lambda function: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500


@app.route('/health')
def health():
    return jsonify({
        'status': 'UP',
        'data': {
            'redis_host': redis_host,
            'redis_port': redis_port,
            'lambda_file': lambda_file
        }
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lucas worker')
    parser.add_argument('--lambda_file', type=str, required=True, help='The lambda file to run')
    parser.add_argument('--function_name', type=str, required=True, help='The function name to run')
    parser.add_argument('--server_port', type=int, default=9000, help='The port to run the server on')
    args = parser.parse_args()
    lambda_file = args.lambda_file
    function_name = args.function_name
    server_port = args.server_port
    # Load the user's lambda function
    try:
        spec = importlib.util.spec_from_file_location(function_name, lambda_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func = getattr(module, function_name)
        def functor(*args):
            return func(*args)
        lambda_handler = functor
    except Exception as e:
        logger.error(f"Failed to load the lambda function: {e}")
        sys.exit(1)
    # Start the HTTP server
    app.run(host='0.0.0.0', port=server_port)