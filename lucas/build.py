import docker
import os
import json
import argparse
from packaging import version
from .clean import move_file_to_lucas_dir


def get_latest_version(image_name):
    client = docker.from_env()
    images = client.images.list()
    versions = []
    for img in images:
        for tag in img.tags:
            if tag.startswith(image_name):
                tag_version = tag.split(":")[1]
                try:
                    parsed_version = version.parse(tag_version)
                    versions.append(parsed_version)
                except version.InvalidVersion:
                    print(f"Invalid version: {tag_version}")
    if versions:
        return f"{image_name}:{max(versions)}"
    else:
        return 'lucas'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lucas build')
    parser.add_argument('--file', type=str, help='json file for image build', default='config.json')
    args = parser.parse_args()

    build_config = args.file
    build_config = json.load(open(build_config, 'r'))
    client = docker.from_env()

    # Dockerfile
    base_image = get_latest_version("lucas")
    print('Base image:', base_image)

    app_name = build_config.get('appname')
    registry = build_config.get('registry', "192.168.28.220:5000")

    functions = build_config['functions']
    for function in functions:
        function_name = function['name']
        function_path = function['path']
        require_file = function.get('require')
        function_image = None
        if app_name is not None:
            function_image = f"{app_name}-{function_name}"
        else:
            function_image = f"{function_name}"
        function_image += ':tmp'
        def generate_docker_file():
            with open(f'{function_image}.dockerfile', 'w') as f:
                f.write(f"FROM {base_image}\n")
                f.write(f"COPY {function_path} /code\n")
                f.write(f"WORKDIR /code\n")
                if require_file:
                    f.write(f"COPY {require_file} /requirements.txt\n")
                    f.write(f"RUN pip install -r /requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/\n")
                f.close()
        generate_docker_file()
        client.images.build(
            path=os.getcwd(),
            tag=function_image,
            dockerfile=f"{function_image}.dockerfile",
            nocache=True
        )

        image = client.images.get(function_image)
        image.tag(f"{registry}/library/{function_image.split(':')[0]}", tag='tmp')

        print(f"Pushing image: {registry}/library/{function_image}")
        for line in client.images.push(f"{registry}/library/{function_image}", stream=True):
            print(line.decode('utf-8').strip())

        # clean up
        for f in os.listdir('.'):
            if f.endswith('.dockerfile'):
                move_file_to_lucas_dir(f)