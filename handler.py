```python
import os
import time
import uuid
import base64
import subprocess
import requests
import runpod


COMFYUI_DIR = "/app/ComfyUI"
COMFYUI_URL = "http://127.0.0.1:8188"

# Timeout máximo de ejecución del workflow (segundos)
WORKFLOW_TIMEOUT = int(os.environ.get("WORKFLOW_TIMEOUT", "300"))
POLL_INTERVAL = 1.0


def start_comfyui():
    print("Iniciando ComfyUI...")

    process = subprocess.Popen(
        ["python", "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd=COMFYUI_DIR,
        stdout=None,
        stderr=None
    )

    print("Esperando a que ComfyUI esté disponible...")

    for i in range(120):
        try:
            response = requests.get(
                f"{COMFYUI_URL}/system_stats",
                timeout=2
            )

            if response.status_code == 200:
                print("ComfyUI iniciado correctamente.")
                return process

        except requests.exceptions.RequestException:
            pass

        time.sleep(1)

    print("ERROR: ComfyUI no ha iniciado correctamente.")
    process.terminate()
    raise RuntimeError("ComfyUI no responde")


def queue_prompt(workflow, client_id):
    """Envía el workflow a ComfyUI y devuelve el prompt_id."""

    api_key = os.environ.get("COMFY_API_KEY")

    if not api_key:
        raise RuntimeError(
            "No se ha encontrado la variable de entorno COMFY_API_KEY"
        )

    payload = {
        "prompt": workflow,
        "client_id": client_id,
        "extra_data": {
            "api_key_comfy_org": api_key
        }
    }

    response = requests.post(
        f"{COMFYUI_URL}/prompt",
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"ComfyUI rechazó el workflow "
            f"({response.status_code}): {response.text}"
        )

    data = response.json()

    if "error" in data:
        raise RuntimeError(
            f"Error de ComfyUI al encolar: {data['error']}"
        )

    prompt_id = data.get("prompt_id")

    if not prompt_id:
        raise RuntimeError(
            f"ComfyUI no devolvió prompt_id: {data}"
        )

    return prompt_id


def wait_for_completion(prompt_id):
    """Hace polling sobre /history/{prompt_id} hasta que el workflow termine."""

    start_time = time.time()

    while True:
        if time.time() - start_time > WORKFLOW_TIMEOUT:
            raise TimeoutError(
                f"El workflow {prompt_id} superó el timeout "
                f"de {WORKFLOW_TIMEOUT}s"
            )

        response = requests.get(
            f"{COMFYUI_URL}/history/{prompt_id}",
            timeout=10
        )

        if response.status_code == 200:
            history = response.json()

            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})

                # ComfyUI marca error en status_str / messages
                if status.get("status_str") == "error":
                    raise RuntimeError(
                        f"El workflow falló en ComfyUI: {status}"
                    )

                if status.get("completed", False):
                    return entry

                # Comprobación de errores de ejecución en los mensajes
                for msg_type, msg_data in status.get("messages", []):
                    if msg_type == "execution_error":
                        raise RuntimeError(
                            f"Error de ejecución: {msg_data}"
                        )

        time.sleep(POLL_INTERVAL)


def fetch_image(filename, subfolder, folder_type):
    """Descarga una imagen generada por ComfyUI y la devuelve en base64."""

    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    }

    response = requests.get(
        f"{COMFYUI_URL}/view",
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return base64.b64encode(response.content).decode("utf-8")


def extract_images(history_entry):
    """Recorre los outputs del history y descarga cada imagen generada."""

    images = []
    outputs = history_entry.get("outputs", {})

    for node_id, node_output in outputs.items():

        for img in node_output.get("images", []):

            b64 = fetch_image(
                img["filename"],
                img.get("subfolder", ""),
                img.get("type", "output")
            )

            images.append({
                "node_id": node_id,
                "filename": img["filename"],
                "data_base64": b64
            })

    return images


def handler(job):

    job_input = job.get("input", {})
    workflow = job_input.get("workflow")

    if not workflow:
        return {
            "status": "error",
            "message": "Falta 'workflow' en el input del job"
        }

    client_id = job_input.get(
        "client_id",
        str(uuid.uuid4())
    )

    try:

        prompt_id = queue_prompt(
            workflow,
            client_id
        )

        print(
            f"Workflow encolado con prompt_id={prompt_id}"
        )

        history_entry = wait_for_completion(
            prompt_id
        )

        images = extract_images(
            history_entry
        )

        return {
            "status": "completed",
            "prompt_id": prompt_id,
            "images": images
        }

    except TimeoutError as e:

        return {
            "status": "timeout",
            "message": str(e)
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


print("========================================")
print("MODARIA SERVERLESS WORKER")
print("========================================")

# Comprobar que la variable existe sin mostrar la clave
if os.environ.get("COMFY_API_KEY"):
    print("COMFY_API_KEY detectada.")
else:
    print("ADVERTENCIA: COMFY_API_KEY no está configurada.")

comfy_process = start_comfyui()

runpod.serverless.start({
    "handler": handler
})
```
