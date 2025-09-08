import os

if os.getenv("DEBUG") == "1":
    try:
        import debugpy  # type: ignore

        debugpy.listen(("0.0.0.0", 5678))
    except Exception as e:
        # Safe with uvicorn workers / reload: ignore if already bound
        if "address already in use" not in str(e).lower():
            raise
    if os.getenv("DEBUG_WAIT") == "1":
        debugpy.wait_for_client()
