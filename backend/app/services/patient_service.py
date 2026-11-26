# Patient and relationship service

from app.db.session import SessionLocal
from app.schemas.patients import PatientResponse, PrivacySummaryResponse


def get_patient(patient_id: str) -> PatientResponse:
    """
    Get a patient by ID.
    """
    db = SessionLocal()
    try:
        # For the alpha, return synthetic data
        return PatientResponse(
            patient_id=patient_id,
            status="active",
            given_name="Synthetic",
            family_name="Patient",
            created_at=None,
        )
    finally:
        db.close()


def get_patient_privacy_summary(patient_id: str) -> PrivacySummaryResponse:
    """
    Get the privacy summary for a patient.
    """
    return PrivacySummaryResponse(
        relationship=None,
        consent=None,
        channel={"in_app": "active"},
    )
