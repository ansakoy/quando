from fastapi import APIRouter, Response

from backend import service
from backend.models import PrescriptionCreate, PrescriptionUpdate
from constants import API_PREFIX

router = APIRouter(prefix=API_PREFIX)


@router.get("/prescriptions/")
def list_prescriptions():
    return service.list_prescriptions()


@router.post("/prescriptions/", status_code=201)
def create_prescription(payload: PrescriptionCreate):
    return service.create_prescription(payload)


@router.get("/prescriptions/{prescription_id}/")
def get_prescription(prescription_id: int):
    return service.get_prescription(prescription_id)


@router.put("/prescriptions/{prescription_id}/")
def replace_prescription(prescription_id: int, payload: PrescriptionUpdate):
    return service.replace_prescription(prescription_id, payload)


@router.delete("/prescriptions/{prescription_id}/", status_code=204)
def delete_prescription(prescription_id: int):
    service.delete_prescription(prescription_id)
    return Response(status_code=204)
