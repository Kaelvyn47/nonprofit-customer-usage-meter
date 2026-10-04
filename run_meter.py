import uvicorn


if __name__ == "__main__":
    uvicorn.run("nonprofit_meter.nonprofit_usage_api:app", host="127.0.0.1", port=8000)
