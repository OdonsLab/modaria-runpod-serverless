import os
import time
import subprocess
import requests
import runpod


COMFYUI_DIR = "/app/ComfyUI"
COMFYUI_URL = "http://127.0.0.1:8188"


def start_comfyui():
    print("Iniciando ComfyUI...")

    process = subprocess.Popen(
        [
            "python",
            "main.py",
            "--listen",
            "127.0.0.1",
            "--port",
            "8188"
        ],
        cwd=COMFYUI_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
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


def handler(job):
    print("Job recibido:", job)

    return {
        "status": "ok",
        "message": "ComfyUI está funcionando dentro del worker",
        "job": job
    }


print("========================================")
print("MODARIA SERVERLESS WORKER")
print("========================================")

comfy_process = start_comfyui()

runpod.serverless.start({
    "handler": handler
})
