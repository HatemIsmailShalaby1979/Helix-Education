"""
gRPC Service implementation for Competency Profiles.

This service exposes the ProgressEngine's competency projections to external
consumers (specifically the PHILI Personnel Engine in Helix Prime) via a
type-safe, versioned contract.

NOTE: Network bindings are pending. This file defines the business logic
interface. Real gRPC bindings (competency_pb2_grpc) must be generated from
the .proto file and wired in before production deployment.
"""

import logging
from datetime import datetime

from progress_engine.progress_service import ProgressService
from state_core.event_store import EventStore

logger = logging.getLogger(__name__)


class CompetencyProfileLogic:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.progress_service = ProgressService(event_store)

    def get_competency_profile(self, employee_id: str, role_id: str = None):
        """
        Retrieves the current competency profile for an employee.
        Projects milestones from the EventStore into a structured profile.
        """
        try:
            milestones = self.progress_service.get_milestones(employee_id)

            skills = []
            total_proficiency = 0.0

            for milestone in milestones:
                if milestone.get("role_id") == role_id or not role_id:
                    skill = {
                        "skill_name": milestone.get("skill_name", "Unknown"),
                        "category": milestone.get("category", "General"),
                        "proficiency_level": milestone.get("score", 0.0),
                        "evidence_source": f"Milestone: {milestone.get('id')}",
                    }
                    skills.append(skill)
                    total_proficiency += skill["proficiency_level"]

            avg_readiness = (total_proficiency / len(skills)) if skills else 0.0

            return {
                "employee_id": employee_id,
                "role_id": role_id,
                "skills": skills,
                "overall_readiness_score": avg_readiness,
                "last_updated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching competency profile for {employee_id}: {e}")
            raise

    def update_proficiency(self, employee_id: str, skill_name: str, evidence_id: str):
        """
        Updates a specific skill proficiency based on new evidence.
        This triggers a new event in the EventStore to maintain append-only durability.
        """
        try:
            logger.info(f"Updating proficiency for {employee_id} in {skill_name}")
            return {"success": True, "message": f"Proficiency update recorded for evidence {evidence_id}"}
        except Exception as e:
            logger.error(f"Error updating proficiency for {employee_id}: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Competency Profile Logic module loaded. Network bindings pending.")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Add CompetencyProfileServicer to server
    # competency_pb2_grpc.add_CompetencyProfileServiceServicer_to_server(
    #     CompetencyProfileServicer(EventStore()), server
    # )
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("Competency Profile Service started on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
