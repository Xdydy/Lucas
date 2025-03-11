import argparse
import requests
import uuid
import json
import time
import os
from kubernetes import config, client
from lucas.storage import RedisDB
from lucas.utils.logging import log as logging

consumer = None
def create_rocketmq_consumer(funcs: list[str]):
    from .storage.rocketmq import RocketMQConsumer
    from rocketmq.client import ConsumeStatus
    def consumer_callback(msg) -> ConsumeStatus:
        topic = msg.topic
        logging.info(f"Received message from topic {topic}")
        try:
            data = json.loads(msg.body)
            id = data['id']
            params = data['params']
            namespace = data['namespace']
            router = data['router']
            metadata_dict = {
                'id': id,
                'params': params,
                'namespace': namespace,
                'router': router,
                'type': 'invoke'
            }
            resp = requests.post(router[topic], json=metadata_dict, headers={'Content-Type': 'application/json'}, proxies={'http': None, 'https': None})
            if resp.status_code != 200:
                logging.error(f"Failed to invoke function {topic}: {resp.text}")
                return ConsumeStatus.RECONSUME_LATER
            logging.info(f"Function {topic}'s response: {resp.json()}")
            return ConsumeStatus.CONSUME_SUCCESS
        except Exception as e:
            return ConsumeStatus.RECONSUME_LATER
    name_server_address = os.getenv('ROCKETMQ_NAME_SERVER_ADDRESS', '10.0.0.101')
    port = int(os.getenv('ROCKETMQ_PORT', 9876))
    global consumer
    consumer = RocketMQConsumer(name_server_address, port, 'lucas', funcs, consumer_callback)
    logging.info(f"RocketMQ consumer started with subscription to topics: {funcs}")
    return 

def clean_redis():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        pod_name = 'redis-pod'
        namespace = 'default'

        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logging.info(f"Deleted pod {pod_name}")
    except Exception as e:
        logging.info(f"redis pod has been removed")
    
    try:
        service_name = 'redis-service'
        v1.delete_namespaced_service(name=service_name, namespace=namespace)
    except Exception as e:
        logging.info(f"redis service has been removed")

    try:
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
                        'imagePullPolicy': 'IfNotPresent',
                        'command': ['redis-server'],
                        'args': ['--io-threads-do-reads', 'yes', '--io-threads', '6'],
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
        time.sleep(2)
        while True:
            resp = v1.read_namespaced_service(name=service_name, namespace=namespace)
            if resp.spec.external_i_ps is not None:
                break
            time.sleep(1)
        logging.info(f"Created service {service_name}")
    except Exception as e:
        logging.error(f"Failed to load kubernetes config: {e}")
        exit(1)

def is_ksvc_ready(service_name):
    try:
        config.load_kube_config()
        api = client.CustomObjectsApi()

        group = "serving.knative.dev"
        version = "v1"
        namespace = "default"
        plural = "services"

        ksvc = api.get_namespaced_custom_object(group, version, namespace, plural, service_name)
        status = ksvc.get('status', {})
        conditions = status.get('conditions', [])
        for condition in conditions:
            if condition.get('type') == 'Ready' and condition.get('status') == 'True':
                return True
        return False
    except Exception as e:
        logging.error(f"Failed to load kubernetes config: {e}")
        return False

def load_data(dirpath):
    logging.info(f"Loading data from {dirpath}")
    redis_host = '10.0.0.100'
    redis_port = 6379
    redis_proxy = RedisDB(host=redis_host, port=redis_port)
    for f in os.listdir(dirpath):
        with open(os.path.join(dirpath, f), 'r') as file:
            redis_proxy.set(file.name.split('/')[-1], file.read())

if __name__ == "__main__":
    clean_redis()
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
        app_config = json.load(f)
    try:
        invoke_config = app_config['inputs']
        params = invoke_config
    except KeyError as e:
        print(f"Failed to load invoke config: {e}")
        exit(1)

    # load data
    redis_data = app_config.get('data', None)
    if redis_data is not None:
        load_redis()
        load_data(redis_data)
    
    functions = app_config['functions']
    namespace = app_config.get('appname', 'default')
    
    # rocketmq
    funcs = [function['name'] for function in functions]
    create_rocketmq_consumer(funcs)


    for function in functions:
        funcname = function['name']
        router[funcname] = f"http://{funcname}.default.10.0.0.233.sslip.io"

    # wait all the router to be ready
    for funcname in router.keys():
        while not is_ksvc_ready(funcname):
            logging.info(f"Waiting for {funcname} to be ready")
            time.sleep(0.5)

    
    _metadata = {
        'id': str(id),
        'params': params,
        'namespace': namespace,
        'router': router,
        'type': type
    }
    logging.info(f"Invoking function {args.function} with metadata {_metadata}")

    start_time = time.time()
    response = requests.post(router[args.function], json=_metadata, headers={'Content-Type': 'application/json'}, proxies={'http': None, 'https': None})
    end_time = time.time()

    
    if response.status_code != 200:
        logging.error(f"Failed to invoke function {args.function}: {response.text}")
        exit(1)
    logging.info(f"Function {args.function} invoked successfully")
    logging.info(f"Response: {response.json()}")
    logging.info(f"Time elapsed: {end_time - start_time} s")

    