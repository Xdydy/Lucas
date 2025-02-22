from setuptools import setup, find_packages

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
            'redis==5.2.1'
        ]
    },
    packages=find_packages(),
    python_requires='>=3.10',
)