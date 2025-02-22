import json
import argparse
import yaml
import os

def generate_kn_obj(registry, funcname, appname):
    if appname == 'default':
        images_name = funcname
    else:
        images_name = f'{appname}-{funcname}'
    kn_obj = {
        'apiVersion': "serving.knative.dev/v1",
        'kind': "Service",
        'metadata': {
            'name': funcname,
            'namespace': "default"
        },
        'spec': {
            'template': {
                'spec': {
                    'containers': [
                        {
                            'image': f'{registry}/library/{images_name}:tmp',
                            'imagePullPolicy': "IfNotPresent",
                            'ports': [{'containerPort': 9000}],
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/health',
                                    'port': 9000
                                },
                                'initialDelaySeconds': 1,
                                'periodSeconds': 3,
                                'timeoutSeconds': 1,
                                'successThreshold': 1,
                                'failureThreshold': 3
                            },
                            'securityContext': {
                                "runAsNonRoot": False,
                                "allowPrivilegeEscalation": False,
                                "capabilities": {
                                    "drop": ['ALL']
                                },
                                "seccompProfile": {
                                    "type": 'RuntimeDefault'
                                }
                            },
                            'command': ['python'],
                            'args': ['-m', 'lucas.worker', '--lambda_file', f"/code/{funcname}.py", '--function_name', 'handler', '--server_port', '9000']
                        }
                    ]
                }
            }
        }
    }
    return yaml.dump(kn_obj)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lucas deploy')
    parser.add_argument('--file', type=str, help='json file for app deploy', default='config.json')
    args = parser.parse_args()

    build_config = args.file
    build_config = json.load(open(build_config, 'r'))
    app_name = build_config.get('appname','default')
    functions = build_config['functions']
    
    registry = build_config.get('registry', '192.168.28.220:5000')
    yaml_list = []
    for function in functions:
        function_name = function['name']
        kn_obj = generate_kn_obj(registry, function_name, app_name)
        yaml_list.append(kn_obj)

    with open(f'{app_name}.yaml', 'w') as f:
        f.write('\n---\n'.join(yaml_list))

    os.system(f'kubectl apply -f {app_name}.yaml')
    

