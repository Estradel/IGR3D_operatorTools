import base64

import pandas
import sqlalchemy
import streamlit as st
import streamlit_pydantic as sp
import streamlit.components.v1 as components

from models.BvhModels import BVHFileCreate, generate_random_bvh_file_create
from tools.db_tools import (
    save_bvh_file_to_db,
    get_postgis_connection,
    BVHFile,
    update_bvh_records_from_dataframe,
    delete_bvh_records
)

st.set_page_config(page_title="Motion Lab Operator Tools", layout="wide")
st.title("🏃‍♂️ Motion Lab Operator Tools")

def load_html_template(bvh_data=""):
    """
    Loads the external HTML file and injects the BVH data
    into the placeholder string.
    """
    with open("viewer.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # 1. Encode the BVH string to Base64 to avoid syntax errors
    bvh_b64 = base64.b64encode(bvh_data.encode('utf-8')).decode('utf-8')

    # 2. Inject the Base64 string
    return html_content.replace("__BVH_BASE64_PLACEHOLDER__", bvh_b64)

engine = get_postgis_connection()

tab1, tab2 = st.tabs(["View and Save BVH file to database", "Edit BVH Database Entries"])
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        # File Uploader
        st.subheader("1. Upload, preview and save a BVH file to the database")
        uploaded_file = st.file_uploader("Upload and preview a BVH file", type=["bvh"])

        # Optionally, provide sample BVH files from a 'data' folder
        from pathlib import Path
        data_folder = Path("data")

        # Bouton pour sauvegarder le fichier uploadé dans le répertoire data
        if uploaded_file is not None:
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                if st.button("💾 Sauvegarder le fichier dans data/", type="primary"):
                    # Créer le répertoire data s'il n'existe pas
                    data_folder.mkdir(exist_ok=True)

                    # Définir le chemin du fichier
                    file_path = data_folder / uploaded_file.name

                    # Vérifier si le fichier existe déjà
                    if file_path.exists():
                        st.warning(f"⚠️ Le fichier '{uploaded_file.name}' existe déjà dans data/")
                    else:
                        # Sauvegarder le fichier
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Fichier '{uploaded_file.name}' sauvegardé dans {file_path}")
                        st.rerun()

            with col_save2:
                if st.button("💾📊 Sauvegarder + Ajouter à la DB", type="secondary"):
                    # Créer le répertoire data s'il n'existe pas
                    data_folder.mkdir(exist_ok=True)

                    # Définir le chemin du fichier
                    file_path = data_folder / uploaded_file.name

                    # Sauvegarder le fichier
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Créer le modèle BVH et sauvegarder en DB
                    try:
                        new_bvh_model = generate_random_bvh_file_create(file_path)
                        save_bvh_file_to_db(engine, new_bvh_model)
                        st.success(f"✅ Fichier sauvegardé et ajouté à la base de données!")
                        sp.pydantic_output(new_bvh_model)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")

        if data_folder.exists():
            bvh_files = [p for p in data_folder.iterdir() if p.is_file() and p.suffix.lower() == ".bvh"]
            if bvh_files:
                st.subheader("2. Or load a sample BVH file from the NAS and save to database")
                selected_file = st.selectbox("Or select a sample BVH file", bvh_files)
                new_bvh_model : BVHFileCreate = None
                col1_1, col1_2 = st.columns(2, width="stretch")
                with col1_1:
                    if st.button("Load Sample File"):
                        uploaded_file = open(selected_file, "rb")
                with col1_2:
                    if st.button("Save Sample BVH File to Database", type="primary"):
                        new_bvh_model : BVHFileCreate = generate_random_bvh_file_create(Path(selected_file))
                        if save_bvh_file_to_db(engine, new_bvh_model):
                            st.success(f"Sample BVH file '{selected_file.name}' saved to database.")
                        else:
                            st.error("Failed to save the sample BVH file to database.")

                if new_bvh_model:
                    sp.pydantic_output(new_bvh_model)

    with col2:
        if uploaded_file is not None:
            # Read file content as string
            bvh_content = uploaded_file.read().decode("utf-8")

            # 2. Inject into HTML Template
            final_html = load_html_template(bvh_content)

            # 3. Render the HTML component
            # Height 600px gives enough room for the viewer
            components.html(final_html, height=600)

        else:
            st.info("Please upload or select a .bvh file to visualize.")

with tab2:
    st.subheader("📊 Éditer les entrées BVH")

    # Charger les données depuis la base
    df = pandas.read_sql_query(
        sql = sqlalchemy.select(BVHFile),
        con = engine
    )

    if df.empty:
        st.info("Aucune entrée dans la base de données.")
    else:
        st.info(f"📝 Vous pouvez éditer directement les cellules ci-dessous. Cliquez sur 'Sauvegarder les modifications' pour enregistrer dans la base de données.")

        # Ajouter une colonne de sélection si elle n'existe pas déjà
        if 'Sélectionner' not in df.columns:
            df.insert(0, 'Sélectionner', False)

        # Colonnes non éditables
        disabled_columns = ['id', 'uuid', 'uploaded_at']

        # Éditeur de données
        edited_df = st.data_editor(
            df,
            width="content",
            num_rows="fixed",  # Pas d'ajout/suppression de lignes
            disabled=disabled_columns,  # Colonnes en lecture seule
            column_config={
                "Sélectionner": st.column_config.CheckboxColumn(
                    "✓",
                    help="Sélectionner cette ligne pour les actions",
                    default=False,
                ),
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "uuid": st.column_config.TextColumn("UUID", disabled=True),
                "uploaded_at": st.column_config.DatetimeColumn("Date Upload", disabled=True),
                "file_path": st.column_config.TextColumn("Chemin"),
                "original_filename": st.column_config.TextColumn("Nom Fichier"),
                "file_size_kb": st.column_config.NumberColumn("Taille (KB)"),
                "duration_seconds": st.column_config.NumberColumn("Durée (s)", format="%.3f"),
                "frame_count": st.column_config.NumberColumn("Nb Frames"),
                "frame_time": st.column_config.NumberColumn("Frame Time", format="%.6f"),
                "fps": st.column_config.NumberColumn("FPS", format="%.2f"),
                "skeleton_type": st.column_config.TextColumn("Type Squelette"),
                "bone_count": st.column_config.NumberColumn("Nb Os"),
                "has_fingers": st.column_config.CheckboxColumn("Doigts"),
                "rest_pose_height": st.column_config.NumberColumn("Hauteur (m)", format="%.2f"),
                "animation_style": st.column_config.TextColumn("Style"),
                "description": st.column_config.TextColumn("Description"),
                "actor_gender": st.column_config.SelectboxColumn(
                    "Genre",
                    options=["M", "F", "Neutral", "Other"],
                ),
                "loopable": st.column_config.CheckboxColumn("Loopable"),
            }
        )

        # Compter les lignes sélectionnées
        selected_rows = edited_df[edited_df['Sélectionner'] == True]
        num_selected = len(selected_rows)

        # Afficher les actions disponibles
        st.divider()
        st.caption(f"**{num_selected}** ligne(s) sélectionnée(s)")

        # Boutons d'action
        action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)

        final_html = None
        with action_col1:
            if st.button("👁️ Preview BVH", type="secondary", width="content", disabled=(num_selected == 0 or num_selected > 1)):
                if num_selected == 1:
                    with st.spinner("Chargement du BVH..."):
                        with open(selected_rows.iloc[0].file_path, "r", encoding="utf-8") as f:
                            bvh_content = f.read()
                            final_html = load_html_template(bvh_content)


        with action_col2:
            if st.button("💾 Sauvegarder les modifications", type="primary", width="content"):
                with st.spinner("Sauvegarde en cours..."):
                    try:
                        # Enlever la colonne de sélection avant de sauvegarder
                        df_to_save = edited_df.drop(columns=['Sélectionner'])
                        updated_count, errors = update_bvh_records_from_dataframe(engine, df_to_save)

                        if errors:
                            st.warning(f"⚠️ {updated_count} ligne(s) mise(s) à jour avec {len(errors)} erreur(s):")
                            for error in errors:
                                st.error(error)
                        else:
                            st.success(f"✅ {updated_count} ligne(s) mise(s) à jour avec succès!")
                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")

        with action_col3:
            if st.button("🗑️ Supprimer sélection", type="secondary", width="content", disabled=(num_selected == 0)):
                if num_selected > 0:
                    ids_to_delete = selected_rows['id'].tolist()
                    deleted_count = delete_bvh_records(engine, ids_to_delete)
                    st.success(f"✅ {deleted_count} ligne(s) supprimée(s)!")
                    st.rerun()

        with action_col4:
            if st.button("📋 Dupliquer sélection", type="secondary", width="content", disabled=(num_selected == 0)):
                if num_selected > 0:
                    st.info(f"Fonctionnalité de duplication en développement pour {num_selected} ligne(s)")

        with action_col5:
            if st.button("📊 Exporter CSV", type="secondary", width="content"):
                csv = edited_df.drop(columns=['Sélectionner']).to_csv(index=False)
                st.download_button(
                    label="⬇️ Télécharger",
                    data=csv,
                    file_name="bvh_export.csv",
                    mime="text/csv",
                    width="content"
                )

        if final_html:
            col1, col2 = st.columns(2)
            with col1:
                components.html(final_html, height=500)
            with col2:
                selected_rows.iloc[0]