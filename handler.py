import runpod


def handler(job):
    job_input = job.get("input", {})

    return {
        "status": "ok",
        "message": "MODARIA Serverless Worker funcionando",
        "input": job_input
    }


runpod.serverless.start({
    "handler": handler
})
