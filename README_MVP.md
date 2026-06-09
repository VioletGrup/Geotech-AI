# Geotech GraphRAG MVP

This refactor turns the original prototype into a working MVP for:

- storing historical geotech and pile load test data in Neo4j,
- querying similar historical cases,
- generating dataset summaries,
- training a pile load capacity model from historical graph data,
- predicting capacity for a new pile and returning similar-case evidence.

## Environment variables

Create a `.env` file or export these variables:

```env
NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
NEO4J_USER=<username>
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
APP_DEBUG=true
ALLOW_RAW_CYPHER=false
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## High-level flow

1. Load / create graph data.
2. Train the model from historical pile load tests:
   - `POST /predict/train`
3. Ask questions / retrieve evidence:
   - `GET /query/summary`
   - `GET /query/similar?...`
   - `POST /query/ask`
4. Predict a new pile load capacity:
   - `POST /predict`

## Example prediction payload

```json
{
  "diameter": 0.6,
  "length": 18.0,
  "qc": 12500,
  "fs": 110,
  "pile_type": "bored",
  "soil_type": "dense sand",
  "site_id": "SITE-01",
  "top_k": 5
}
```
