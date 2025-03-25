***Application***
1) Change ```.envcopy``` to ```.env```, then add values to the associated keys below (```.envcopy``` can be found in the main directory):
`MISTRAL_API_KEY`
`DB_USER`
`DB_PASSWORD`
`DB_NAME`
`DB_PORT`
`DB_HOST`

2) Run ```docker-compose -f docker-compose.yml up --build``` with docker running to start app in container

3) To shutdown the application, run ```docker-compose -f docker-compose.yml down```; if you would like to "forget" the data added to the database and redis, run the command with the ```-v``` tag at the end i.e. ```docker-compose down -v```

***Extras***

For connecting and testing db:
```docker exec -it CONTAINER_NAME-db-1 psql -U DB_USER -d DB_NAME -h DB_HOST -p DB_PORT```

```docker exec -it guidepoint_assignment-db-1 psql -U senan -d app_db -h db -p 5432```

For connecting to redis container:
```docker exec -it CONTAINER_NAME-redis-1 redis-cli```
```docker exec -it guidepoint_assignment-redis-1 redis-cli```

For running tests:
```python -m pytest -v -s test```

For running locust:
```locust -f locustfile.py --host=http://localhost:8000```

***Decisions:***
- **pgvector** for similarity search
    - Avoids extra dependencies while providing efficient vector search.
- **Celery + Redis** for task execution
    - *Celery* handles long-running tasks (PDF processing, embedding generation).
    - *Redis as a broker* ensures efficient task distribution.
    - Robust task queueing, automatic retries and distributed processing as well as being easy to implement
- **Redis** for caching
    - Reduces response time for repeated queries by storing computed results.
    - light-weight inmemory data store
- **LLM**
    - Running a local LLM is too resource-intensive.
    - Using Mistral API for LLM inference since it keeps the setup lightweight and is free.
    - NOTE: Would be ideal to use Mistral for both embeddings + invocation since free and no need for extra embedding library
- **Embeddings**:
    - Mistral API for embeddings (preferred, free, no extra dependencies).
    - SentenceTransformers (open-source and in-memory alternative); specific to "open-source and in-memory" condition specified in assignment
        - Lower similarity threshold due to:
            1) Lower dimensional vector space, smaller vector space leads to larger changes in similarity values with small changes in input.
            2) May not capture as much fine-grained semantic meaning as a heavily fine-tuned proprietary model.
- **pdpdf** for text extraction from PDFs.
- **gunicorn** for parallization of API requests
    - 8 workers: Each worker handles endpoints calls independently
    - reduce latency for multiple requests

- locust shows that biggest bottle neck is API calls to invoke the LLM, with failures due to the max 1 request per second and time taken to process invocation + db query ~1.5s

What to improve:
- Implement async + await to enforce rate limit calls to LLM API in answer_question route to prevent failuers
    - Using a queue-based approach
    - Limited scalability comes from LLM rate limit
        - Could try distributing requests across multiple API keys to see if this works.

