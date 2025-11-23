import yaml
from pathlib import Path


def ensure_readonly_root_filesystem(manifest_path: Path):
    with open(manifest_path) as f:
        manifests = list(yaml.safe_load_all(f))

    modified = False
    new_manifests = []

    for doc in manifests:
        if doc is None:
            new_manifests.append(doc)
            continue

        kind = doc.get("kind")
        if kind in ["Deployment", "StatefulSet", "CronJob", "Job"]:
            # Handle Deployment, StatefulSet, Job
            containers_path = ["spec", "template", "spec", "containers"]
            init_containers_path = ["spec", "template", "spec", "initContainers"]

            # Handle CronJob specific path
            if kind == "CronJob":
                containers_path = ["spec", "jobTemplate", "spec", "template", "spec", "containers"]
                init_containers_path = ["spec", "jobTemplate", "spec", "template", "spec", "initContainers"]

            for c_path in [containers_path, init_containers_path]:
                current_containers = doc
                for key in c_path:
                    if isinstance(current_containers, dict) and key in current_containers:
                        current_containers = current_containers[key]
                    elif isinstance(current_containers, list):
                        break  # will iterate over list below
                    else:
                        current_containers = None
                        break

                if isinstance(current_containers, list):
                    for container in current_containers:
                        if "securityContext" not in container:
                            container["securityContext"] = {}
                            modified = True
                        if container["securityContext"].get("readOnlyRootFilesystem") is not True:
                            container["securityContext"]["readOnlyRootFilesystem"] = True
                            modified = True
        new_manifests.append(doc)

    if modified:
        with open(manifest_path, "w") as f:
            yaml.safe_dump_all(new_manifests, f, indent=2, sort_keys=False)
        print(f"✅ Modified {manifest_path} to ensure readOnlyRootFilesystem: true")
        return True
    print(f"ℹ️ No changes needed for {manifest_path}")
    return False


# List of files to process
manifest_files = [
    "deployments/overlays/production-gke/deployment-patch.yaml",
    "deployments/overlays/production-gke/keycloak-patch.yaml",
    "deployments/overlays/production-gke/openfga-patch.yaml",
    "deployments/overlays/production/deployment-patch.yaml",
    "deployments/overlays/production/otel-collector-patch.yaml",
    "deployments/overlays/production/postgres-patch.yaml",
    "deployments/overlays/production/qdrant-patch.yaml",
    "deployments/overlays/production/redis-session-patch.yaml",
    "deployments/overlays/staging-gke/keycloak-patch.yaml",
    "deployments/overlays/staging-gke/otel-collector-patch.yaml",
    "deployments/overlays/staging/deployment-patch.yaml",
    "deployments/overlays/staging/otel-collector-patch.yaml",
    "deployments/kubernetes/kong/kong-jwks-updater-cronjob.yaml",
    "deployments/kubernetes/kong/redis-deployment.yaml",
    "deployments/optimized/postgres-statefulset.yaml",
    "deployments/overlays/dev/deployment-patch.yaml",
    "deployments/overlays/dev/otel-collector-patch.yaml",
    "deployments/overlays/dev/postgres-patch.yaml",
    "deployments/overlays/dev/qdrant-patch.yaml",
    "deployments/overlays/dev/redis-session-patch.yaml",
    "deployments/kubernetes/overlays/aws/deployment-patch.yaml",
]

if __name__ == "__main__":
    total_modified = 0
    for file_path_str in manifest_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            if ensure_readonly_root_filesystem(file_path):
                total_modified += 1
        else:
            print(f"⚠️ Manifest file not found: {file_path}")

    if total_modified > 0:
        print(f"Summary: Modified {total_modified} manifest files.")
    else:
        print("Summary: No manifest files needed modification.")
