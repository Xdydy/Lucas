from kubernetes import client, config
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

if __name__ == '__main__':
    delete_all_ksvc()