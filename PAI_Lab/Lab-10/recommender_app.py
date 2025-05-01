import streamlit as st
import weaviate
import weaviate.classes as wvc
from openai import OpenAI
import os
from dotenv import load_dotenv
from weaviate.util import generate_uuid5

load_dotenv()
hugging_face_apikey = os.getenv("HUGGINGFACE_API_KEY")
weaviate_url = os.getenv("WEAVIATE_URL")
weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
openrouter_apikey = os.getenv("OPENROUTER_KEY")
LLM_model = os.getenv("LLM_MODEL")
base_url = os.getenv("BASE_URL")


def LLM_chat(prompt_text):
    completion = LLM_client.chat.completions.create(
        model=LLM_model,
        messages=[
            {"role": "system", "content": "You are a movie recommendation assistant"},
            {"role": "user", "content": prompt_text},
        ],
    )
    return completion.choices[0].message.content


def connect_to_db():
    client = weaviate.connect_to_wcs(
        cluster_url=weaviate_url,
        auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
        headers={"X-HuggingFace-Api-Key": hugging_face_apikey},
    )
    print("Connected Successfully")
    return client


def LLM_config():
    return OpenAI(base_url=base_url, api_key=openrouter_apikey)


def prompt(response, query, occasion):
    movies_context = []
    for obj in response.objects:
        # Access the linked movie properties through references
        movie_ref = obj.references["hasMovie"].objects[0].properties
        movies_context.append(
            f"Title: {movie_ref['title']}\n"
            f"Movie ID: {movie_ref['movie_id']}\n"
            f"Description: {movie_ref['description']}\n\n"
        )

    return f"""
**Generate Recommendation Report: {query} Films for {occasion}**

=== Contextual Framework ===
1. **User Intent Analysis**
"Acknowledging your interest in {query} experiences{'' if occasion.lower() == 'any occasion' else f' suitable for {occasion}'}, 
we've analyzed patterns in cinematic narratives through:

- Thematic relevance to search parameters
- Narrative depth and engagement potential
- Contextual alignment with {occasion.replace('any ', '').lower()} scenarios

=== Key Film Data ===
{''.join(movies_context)}

=== Recommendation Guidelines ===
For each movie, emphasize:
1. How the description's narrative elements align with {query}
2. Unique aspects of the story that suit {occasion}
3. Emotional resonance and thematic relevance
4. Comparative strengths between recommendations
5. Professional tone with vivid but concise language
"""


LLM_client = LLM_config()
client = connect_to_db()
movies = client.collections.get("Movie")
reviews = client.collections.get("Review")
synopsis_collection = client.collections.get("Synopsis")

try:
    st.title("CineMatch")
    search_tab, movie_tab, rec_tab = st.tabs(["Search", "Movie details", "Recommend"])

    with search_tab:
        st.header("Search for a movie")
        query_string = st.text_input(label="Search a movie")

        srch_col1, srch_col2 = st.columns(2)
        with srch_col1:
            search_type = st.radio(
                label="How do you want to search?", options=["Vector", "Hybrid"]
            )
        with srch_col2:
            value_range = st.slider(label="Rating Range", value=(0.0, 5.0), step=0.1)

        st.header("Search results")
        movie_filter = wvc.query.Filter.by_property("rating").greater_or_equal(
            value_range[0]
        ) & wvc.query.Filter.by_property("rating").less_or_equal(value_range[1])

        synopsis_xref = wvc.query.QueryReference(
            link_on="hasSynopsis", return_properties=["body"]
        )

        if len(query_string) > 0:
            if search_type == "Vector":
                response = movies.query.near_text(
                    query=query_string,
                    filters=movie_filter,
                    limit=5,
                    return_references=[synopsis_xref],
                )
            else:
                response = movies.query.hybrid(
                    query=query_string,
                    filters=movie_filter,
                    limit=5,
                    return_references=[synopsis_xref],
                )
        else:
            response = movies.query.fetch_objects(
                filters=movie_filter,
                limit=5,
                return_references=[synopsis_xref],
            )

        for movie in response.objects:
            with st.expander(movie.properties["title"]):
                rating = movie.properties["rating"]
                movie_id = movie.properties["movie_id"]
                st.write(f"**Movie rating**: {rating}, **ID**: {movie_id}")
                synopsis_text = (
                    movie.references["hasSynopsis"].objects[0].properties["body"]
                )
                st.write("**Synopsis**")
                st.write(synopsis_text[:200] + "...")

    with movie_tab:
        st.header("Movie details")
        title_input = st.text_input(
            label="Enter the movie row ID here (0-120)", value=""
        )
        if len(title_input) > 0:
            movie_uuid = generate_uuid5(int(title_input))
            movie = movies.query.fetch_object_by_id(
                uuid=movie_uuid,
                return_references=[
                    wvc.query.QueryReference(
                        link_on="hasSynopsis", return_properties=["body"]
                    ),
                ],
            )
            title = movie.properties["title"]
            director = movie.properties["director"]
            rating = movie.properties["rating"]
            movie_id = movie.properties["movie_id"]
            year = movie.properties["year"]
            st.header(title)
            st.write(f"Director: {director}")
            st.write(f"Rating: {rating}")
            st.write(f"Movie ID: {movie_id}")
            st.write(f"Year: {year}")
            with st.expander("See synopsis"):
                st.write(movie.references["hasSynopsis"].objects[0].properties["body"])

    with rec_tab:
        st.header("Recommend me a movie")
        search_string = st.text_input(label="Recommend me a ...", value="")
        occasion = st.text_input(label="In this context ...", value="any occasion")

        if len(search_string) > 0 and len(occasion) > 0:
            st.subheader("Recommendations")

            response = synopsis_collection.query.hybrid(
                query=search_string,
                limit=3,
                return_references=[
                    wvc.query.QueryReference(
                        link_on="hasMovie",
                        return_properties=["title", "movie_id", "description"],
                    ),
                ],
            )

            prompt_text = prompt(response, search_string, occasion)
            generated_response = LLM_chat(prompt_text)
            st.write(generated_response)

            st.subheader("Movies analysed")
            for i, m in enumerate(response.objects):
                movie_title = m.references["hasMovie"].objects[0].properties["title"]
                movie_id = m.references["hasMovie"].objects[0].properties["movie_id"]
                movie_description = (
                    m.references["hasMovie"].objects[0].properties["description"]
                )
                with st.expander(f"Movie title: {movie_title}, ID: {movie_id}"):
                    st.write(movie_description)

finally:
    client.close()
    print("Connection Closed")
