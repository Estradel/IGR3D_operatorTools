import os

import streamlit as st
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, URL
from sqlalchemy.orm import sessionmaker, declarative_base

st.set_page_config(layout="wide")
st.title("🏃‍♂️ Test database")

Base = declarative_base()

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

db_url = URL.create(
    "postgresql",
    username=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('POSTGRES_HOST'),
    port=os.getenv('POSTGRES_PORT'),
    database=os.getenv('POSTGRES_DB'),
)
engine = create_engine(db_url)
Base.metadata.create_all(engine)

with st.form("my_form"):
    st.write("Inside the form")
    my_number = st.slider('Pick a number', 1, 10)
    my_color = st.selectbox('Pick a color', ['red','orange','green','blue','violet'])
    st.form_submit_button('Submit my picks')

# This is outside the form
st.write(my_number)
st.write(my_color)

if st.button("Add test user to database"):
    Session = sessionmaker(bind=engine)
    session = Session()
    new_user = User(name="John Doe", email="john.doe@example.com")
    session.add(new_user)
    session.query()
    session.commit()
    session.close()
    st.success("Added test user to database")