import enum
import random
import uuid
from datetime import datetime
from pathlib import Path

from faker import Faker

from pydantic import Field, ConfigDict, BaseModel

from sqlalchemy.orm import declarative_base

fake = Faker()
Base = declarative_base()

# 1. Définition de l'Enum pour le genre (pour la validation stricte)
class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"
    Neutral = "Neutral"
    Other = "Other"


# 1. BASE : Les champs partagés
class BVHFileBase(BaseModel):
    original_filename: str = Field(..., min_length=1, max_length=255)

    # Infos techniques
    file_size_kb: int = Field(None, ge=0)
    duration_seconds: float = Field(..., gt=0, description="Durée en secondes")
    frame_count: int = Field(..., gt=0)
    frame_time: float = Field(..., gt=0)
    fps: float = Field(..., gt=0)

    # Structure
    skeleton_type: str = Field(..., max_length=50, example="MIXAMO")
    bone_count: int = Field(..., gt=0)
    has_fingers: bool = False
    rest_pose_height: float = None

    # Contenu
    animation_style: str = Field(None, max_length=100)
    description: str = None
    actor_gender: GenderEnum = None
    loopable: bool = False

# 2. CREATE : Ce qu'on utilise pour insérer (Input)
class BVHFileCreate(BVHFileBase):
    # Le file_path est souvent généré par le backend après l'upload,
    # mais si votre script d'analyse le fournit, on le met ici.
    file_path: str = Field(..., max_length=512)

# 3. READ : Ce que l'API renvoie (Output)
class BVHFileRead(BVHFileBase):
    id: int
    uuid: uuid.UUID
    file_path: str # On renvoie le chemin (ou une URL signée dans une vraie app)
    uploaded_at: datetime

    # CONFIGURATION CRUCIALE POUR ORM
    # Permet à Pydantic de lire directement l'objet SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

def generate_random_bvh_file_create(path : Path) -> BVHFileCreate:
    """Génère un objet BVHFileCreate avec des valeurs aléatoires.
    :param path:
    """

    animation_styles = ["Walk", "Run", "Jump", "Dance", "Idle", "Combat", "Gesture"]
    skeleton_types = ["MIXAMO", "CUSTOM", "CMU", "BIPED"]

    return BVHFileCreate(
        # Nom de fichier
        original_filename=path.name,
        file_path=str(path.absolute()),

        # Infos techniques
        file_size_kb=random.randint(50, 5000),
        duration_seconds=round(random.uniform(1.0, 60.0), 3),
        frame_count=random.randint(30, 1800),
        frame_time=round(random.uniform(0.008, 0.033), 6),
        fps=round(random.uniform(24.0, 120.0), 2),

        # Structure
        skeleton_type=random.choice(skeleton_types),
        bone_count=random.randint(15, 80),
        has_fingers=random.choice([True, False]),
        rest_pose_height=round(random.uniform(1.5, 2.0), 2),

        # Contenu
        animation_style=random.choice(animation_styles),
        description=fake.sentence(nb_words=10),
        actor_gender=random.choice(list(GenderEnum)),
        loopable=random.choice([True, False])
    )