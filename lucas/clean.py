from kubernetes import client, config
import os
import logging

logging.basicConfig(level=logging.INFO)
def delete_all_ksvc():
    try:
        config.load_kube_config()
        api = client.CustomObjectsApi()

        group = "serving.knative.dev"
        version = "v1"
        namespace = "default"
        plural = "services"

        ksvc_list = api.list_namespaced_custom_object(group, version, namespace, plural)
        for ksvc in ksvc_list.get("items"):
            name = ksvc['metadata']['name']
            api.delete_namespaced_custom_object(group, version, namespace, plural, name)
            logging.info(f"Deleted ksvc {name}")
    except Exception as e:
        logging.error(f"Failed to delete ksvc: {e}")

def move_file_to_lucas_dir(filename):
    if not os.path.exists('.lucas'):
        os.mkdir('.lucas')
    os.rename(filename, f'.lucas/{filename}')

if __name__ == '__main__':
    delete_all_ksvc()