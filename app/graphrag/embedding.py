from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer()

def embed_texts(texts):
    return vectorizer.fit_transform(texts).toarray()

def embed_single(text):
    return vectorizer.fit_transform([text]).toarray()[0]