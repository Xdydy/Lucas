from setuptools import setup, find_packages
import os
def get_lib_files():
    lib_dir = os.path.join("lucas", "lib")
    return [os.path.join(lib_dir, f) for f in os.listdir(lib_dir)]

setup(
    name='lucas',
    version='1.0.0',
    author='dydy',
    description='Serverless Orchestration runtime support',
    install_requires=[
        "pydantic==1.10.8",
        "python-dotenv==1.0.1"
    ],
    extras_require={
        'kn': [
            "requests==2.26.0",
            'redis==5.2.1',
            'rocketmq-client-python==2.0.1rc1'
        ],
        "cluster": [
            "pyyaml==1.1",
        ]
    },
    packages=find_packages(),
    package_data= {
        'rocketmq': ["lib/*.so"]
    },
    include_package_data=True,
    python_requires='>=3.10',
)