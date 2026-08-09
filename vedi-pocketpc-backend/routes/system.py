from fastapi import APIRouter, Depends
from routes.pairing import verify_token_header
import input_control

router = APIRouter(dependencies=[Depends(verify_token_header)])

@router.post("/lock")
def lock_pc():
    """
    Locks the host machine.
    """
    success = input_control.system_lock()
    return {"status": "success" if success else "failed"}

@router.post("/sleep")
def sleep_pc():
    """
    Puts the host machine to sleep.
    """
    success = input_control.system_sleep()
    return {"status": "success" if success else "failed"}

@router.post("/shutdown")
def shutdown_pc():
    """
    Shuts down the host machine (delayed by 5 seconds).
    """
    success = input_control.system_shutdown()
    return {"status": "success" if success else "failed"}
