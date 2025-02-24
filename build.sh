python setup.py bdist_wheel
sudo rm -rf ~/.pypi/lucas-1.0.0-py3-none-any.whl
twine upload --repository-url http://localhost:12121/ dist/* -u "faasit" -p "faasit-pypi" --verbose
cd docker/kn
docker build -t lucas:1.0 --no-cache .