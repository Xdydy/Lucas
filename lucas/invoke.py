import argparse
import requests
from .serverless_function import Metadata
import uuid
import json
import logging
import time
from kubernetes import config, client

logging.basicConfig(level=logging.INFO)

def clean_redis():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        pod_name = 'redis-pod'
        namespace = 'default'

        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logging.info(f"Deleted pod {pod_name}")

        service_name = 'redis-service'
        v1.delete_namespaced_service(name=service_name, namespace=namespace)

        # wait for service to be deleted
        while True:
            try:
                v1.read_namespaced_service(name=service_name, namespace=namespace)
                time.sleep(1)
            except Exception as e:
                break
        while True:
            try:
                v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                time.sleep(1)
            except Exception as e:
                break
        logging.info(f"Deleted service {service_name}")
        logging.info(f"Deleted pod {pod_name}")
    except Exception as e:
        logging.error(f"Failed to delete kubernetes config: {e}")

def load_redis():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        pod_name = 'redis-pod'
        container_name = 'redis'
        namespace = 'default'

        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                'labels': {
                    'app': 'redis'
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": container_name,
                        "image": "redis",
                        'imagePullPolicy': 'IfNotPresent'
                    }
                ]
            }
        }

        v1.create_namespaced_pod(namespace=namespace, body=pod_manifest)
        logging.info(f"Created pod {pod_name}")

        while True:
            resp = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            if resp.status.phase == 'Running':
                break
            time.sleep(1)
        logging.info(f"Pod {pod_name} is running")

        service_name = 'redis-service'
        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name
            },
            "spec": {
                "selector": {
                    "app": "redis"
                },
                "ports": [
                    {
                        "port": 6379,
                    }
                ],
                "externalIPs": [
                    "10.0.0.100"
                ]
            }
        }

        v1.create_namespaced_service(namespace=namespace, body=service_manifest)
        logging.info(f"Created service {service_name}")
    except Exception as e:
        logging.error(f"Failed to load kubernetes config: {e}")
        exit(1)

if __name__ == "__main__":
    clean_redis()
    load_redis()
    parser = argparse.ArgumentParser(description='invoke function')
    parser.add_argument('--function', type=str, help='function to invoke', required=True)
    parser.add_argument('--file', type=str, help='json file for invoke', default='config.json')
    args = parser.parse_args()

    id = uuid.uuid4()
    params = None
    namespace = None
    router = {}
    type = 'invoke'
    with open(args.file, 'r') as f:
        config = json.load(f)
    try:
        invoke_config = config['inputs']
        params = invoke_config
    except KeyError as e:
        print(f"Failed to load invoke config: {e}")
        exit(1)
    
    functions = config['functions']
    namespace = config.get('appname', 'default')
    for function in functions:
        funcname = function['name']
        router[funcname] = f"http://{funcname}.default.10.0.0.233.sslip.io"

    
    _metadata = {
        'id': str(id),
        'params': params,
        'namespace': namespace,
        'router': router,
        'type': type
    }
    logging.info(f"Invoking function {args.function} with metadata {_metadata}")
    response = requests.post(router[args.function], json=_metadata, headers={'Content-Type': 'application/json'}, proxies={'http': None, 'https': None})
    
    if response.status_code != 200:
        logging.error(f"Failed to invoke function {args.function}: {response.text}")
        exit(1)
    logging.info(f"Function {args.function} invoked successfully")
    logging.info(f"Response: {response.json()}")

    