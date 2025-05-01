import weaviate
import weaviate.classes.config as wc
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

synopsis = client.collections.create(
    name="Synopsis",
    vectorizer_config=wc.Configure.Vectorizer.text2vec_huggingface(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ),
    properties=[
        wc.Property(
            name="body",
            data_type=wc.DataType.TEXT,
        ),
    ],
)

reviews = client.collections.create(
    name="Review",
    vectorizer_config=wc.Configure.Vectorizer.text2vec_huggingface(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ),
    properties=[
        wc.Property(
            name="body",
            data_type=wc.DataType.TEXT,
        ),
    ],
)
movies = client.collections.create(
    name="Movie",
    vectorizer_config=wc.Configure.Vectorizer.text2vec_huggingface(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ),
    properties=[
        wc.Property(name="title", data_type=wc.DataType.TEXT),
        wc.Property(name="description", data_type=wc.DataType.TEXT),
        wc.Property(name="movie_id", data_type=wc.DataType.INT),
        wc.Property(name="year", data_type=wc.DataType.INT),
        wc.Property(name="rating", data_type=wc.DataType.NUMBER),
        wc.Property(
            name="director", data_type=wc.DataType.TEXT, skip_vectorization=True
        ),
    ],
)
print("collections Created")

# add references to collections
movies = client.collections.get("Movie")
reviews = client.collections.get("Review")
synopsis = client.collections.get("Synopsis")
print("Collections fetched")

movies.config.add_reference(
    wc.ReferenceProperty(name="hasSynopsis", target_collection="Synopsis")
)

movies.config.add_reference(
    wc.ReferenceProperty(name="hasReview", target_collection="Review")
)

synopsis.config.add_reference(
    wc.ReferenceProperty(name="hasMovie", target_collection="Movie")
)
print("References Created, all done.")

# client.collections.delete_all()
client.close()
