import streamlit as st
import os
import uuid
import enum

from dotenv import load_dotenv
from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, Text,
    DateTime, func, Index, Enum as SAEnum, URL, create_engine, Engine
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker

from models.BvhModels import BVHFileCreate

load_dotenv()

Base = declarative_base()

class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"
    Neutral = "Neutral"
    Other = "Other"


class BVHFile(Base):
    __tablename__ = 'bvh'

    # 1. IDENTIFIANT UNIQUE
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Utilisation de uuid.uuid4 pour générer coté Python si besoin,
    # mais 'server_default' laisse Postgres le faire via gen_random_uuid()
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, server_default=func.gen_random_uuid())

    # 2. LOCALISATION
    file_path = Column(String(512), nullable=False, unique=False)
    original_filename = Column(String(255), nullable=False)
    # 'func.now()' utilise l'heure du serveur DB
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # 3. INFOS TECHNIQUES
    file_size_kb = Column(Integer)
    # Numeric(10, 3) = 10 chiffres au total, dont 3 après la virgule
    duration_seconds = Column(Numeric(10, 3))
    frame_count = Column(Integer)
    frame_time = Column(Numeric(10, 6))
    fps = Column(Numeric(5, 2))

    # 4. STRUCTURE DU SQUELETTE
    skeleton_type = Column(String(50))
    bone_count = Column(Integer)
    has_fingers = Column(Boolean, default=False)
    rest_pose_height = Column(Numeric(5, 2))

    # 5. CONTENU & SÉMANTIQUE
    animation_style = Column(String(100))
    description = Column(Text)

    # Mapping de l'Enum Python vers la colonne SQL
    actor_gender = Column(SAEnum(GenderEnum, name='gender_enum'), nullable=True)

    loopable = Column(Boolean, default=False)

    # DÉFINITION DES INDEX
    __table_args__ = (
        # Index standard sur le style
        Index('idx_bvh_style', 'animation_style'),
        # Index standard sur les FPS
        Index('idx_bvh_fps', 'fps'),
    )

    def __repr__(self):
        return f"<BVHFile(id={self.id}, name='{self.original_filename}', style='{self.animation_style}')>"



@st.cache_resource
def get_postgis_connection():
    db_url = URL.create(
        "postgresql",
        username=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST',os.getenv('POSTGRES_HOST_LOCALHOST')),
        port=os.getenv('POSTGRES_PORT'),
        database=os.getenv('POSTGRES_DB'),
    )
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    return engine

def save_bvh_file_to_db(engine : Engine, bvh_data: BVHFileCreate) -> BVHFile:
    """Enregistre un BVHFileCreate dans la base de données."""

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Créer l'objet ORM à partir des données Pydantic
        new_bvh = BVHFile(**bvh_data.model_dump())

        # Ajouter à la session et commiter
        session.add(new_bvh)
        session.commit()

        # Rafraîchir pour obtenir l'ID généré
        session.refresh(new_bvh)

        return new_bvh

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_bvh_records_from_dataframe(engine: Engine, updated_df):
    """Met à jour les enregistrements BVH dans la base de données à partir d'un DataFrame.

    Args:
        engine: Le moteur de base de données SQLAlchemy
        updated_df: Le DataFrame Pandas avec les modifications

    Returns:
        Tuple (nombre de lignes mises à jour, liste des erreurs)
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    updated_count = 0
    errors = []

    try:
        for _, row in updated_df.iterrows():
            try:
                # Récupérer l'enregistrement existant par ID
                bvh_record = session.query(BVHFile).filter_by(id=row['id']).first()

                if bvh_record:
                    # Mettre à jour tous les champs modifiables
                    bvh_record.original_filename = row['original_filename']
                    bvh_record.file_path = row['file_path']
                    bvh_record.file_size_kb = int(row['file_size_kb']) if row['file_size_kb'] else None
                    bvh_record.duration_seconds = float(row['duration_seconds']) if row['duration_seconds'] else None
                    bvh_record.frame_count = int(row['frame_count']) if row['frame_count'] else None
                    bvh_record.frame_time = float(row['frame_time']) if row['frame_time'] else None
                    bvh_record.fps = float(row['fps']) if row['fps'] else None
                    bvh_record.skeleton_type = row['skeleton_type']
                    bvh_record.bone_count = int(row['bone_count']) if row['bone_count'] else None
                    bvh_record.has_fingers = bool(row['has_fingers'])
                    bvh_record.rest_pose_height = float(row['rest_pose_height']) if row['rest_pose_height'] else None
                    bvh_record.animation_style = row['animation_style']
                    bvh_record.description = row['description']
                    bvh_record.actor_gender = row['actor_gender']
                    bvh_record.loopable = bool(row['loopable'])

                    updated_count += 1

            except Exception as e:
                errors.append(f"Erreur ligne id={row.get('id', '?')}: {str(e)}")

        # Commit toutes les modifications
        session.commit()

        return updated_count, errors

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_bvh_records(engine: Engine, ids_to_delete: list) -> int:
    """Supprime les enregistrements BVH avec les IDs spécifiés.

    Args:
        engine: Le moteur de base de données SQLAlchemy
        ids_to_delete: Liste des IDs à supprimer

    Returns:
        Le nombre d'enregistrements supprimés
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    deleted_count = 0


    # Supprimer tous les enregistrements avec les IDs fournis
    deleted_count = session.query(BVHFile).filter(BVHFile.id.in_(ids_to_delete)).delete(synchronize_session=False)
    session.commit()


    session.close()
