import weaviate
import weaviate.classes as wvc
from weaviate.util import generate_uuid5
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
hugging_face_apikey = os.getenv("HUGGINGFACE_API_KEY")
weaviate_url = os.getenv("WEAVIATE_URL")
weaviate_api_key = os.getenv("WEAVIATE_API_KEY")


def connect_to_db():
    client = weaviate.connect_to_wcs(
        cluster_url=weaviate_url,
        auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
        headers={
            "X-HuggingFace-Api-Key": hugging_face_apikey,
        },
    )
    print("Connected Successfully")
    return client


client = connect_to_db()

movies = client.collections.get("Movie")
reviews = client.collections.get("Review")
synopsis = client.collections.get("Synopsis")

movie_df = pd.read_csv("movies_data.csv")

review_objects = list()

for i, row in movie_df.iterrows():
    for c in [1, 2, 3]:
        col_name = f"Critic Review {c}"
        if len(row[col_name]) > 0:
            props = {
                "body": row[col_name],
            }
            review_uuid = generate_uuid5(row[col_name])
            data_obj = wvc.data.DataObject(properties=props, uuid=review_uuid)
            review_objects.append(data_obj)

response = reviews.data.insert_many(review_objects)
print("Data Inserted into review collection.")


movie_objs = list()
for i, row in movie_df.iterrows():
    props = {
        "title": row["Movie Title"],
        "description": row["Description"],
        "rating": row["Star Rating"],
        "director": row["Director"],
        "movie_id": row["ID"],
        "year": row["Year"],
    }

    review_uuids = list()
    for c in [1, 2, 3]:
        col_name = f"Critic Review {c}"
        if len(row[col_name]) > 0:
            review_uuid = generate_uuid5(row[col_name])
            review_uuids.append(review_uuid)

    movie_uuid = generate_uuid5(row["ID"])
    data_obj = wvc.data.DataObject(
        properties=props,
        uuid=movie_uuid,
        references={"hasReview": review_uuids},
    )
    movie_objs.append(data_obj)

response = movies.data.insert_many(movie_objs)
print("Data Inserted into movie collection.")

# Insert Synopses with proper references
synopsis_objects = list()
for i, row in movie_df.iterrows():
    props = {
        "body": row["Synopsis"],
    }

    movie_uuid = generate_uuid5(row["ID"])

    data_obj = wvc.data.DataObject(
        properties=props, uuid=movie_uuid, references={"hasMovie": movie_uuid}
    )
    synopsis_objects.append(data_obj)

response = synopsis.data.insert_many(synopsis_objects)

synopsis_refs = list()
for i, row in movie_df.iterrows():
    movie_uuid = generate_uuid5(row["ID"])
    synopsis_uuid = generate_uuid5(row["Synopsis"])
    ref_obj = wvc.data.DataReference(
        from_property="hasSynopsis", from_uuid=movie_uuid, to_uuid=movie_uuid
    )
    synopsis_refs.append(ref_obj)

response = movies.data.reference_add_many(synopsis_refs)
print("All done")
client.close()
