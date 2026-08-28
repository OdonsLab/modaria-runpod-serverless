import runpod


def handler(job):
    return {
        "status": "ok",
        "message": "MODARIA Serverless Worker funcionando"
    }


runpod.serverless.start(handler)
